"""
Configuration Management System

Provides a flexible configuration system with support for:
- Multiple configuration sources (files, env vars, runtime)
- Schema validation
- Dynamic reloading
- Configuration inheritance
- Secret management
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field, asdict
import logging
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigSource(ABC):
    """Abstract base class for configuration sources"""
    
    @abstractmethod
    async def load(self) -> Dict[str, Any]:
        """Load configuration from source"""
        pass
        
    @abstractmethod
    async def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to source"""
        pass
        
    @abstractmethod
    def get_priority(self) -> int:
        """Get source priority (lower = higher priority)"""
        pass


class EnvConfigSource(ConfigSource):
    """Load configuration from environment variables"""
    
    def __init__(self, prefix: str = "MEM0_"):
        self.prefix = prefix
        
    async def load(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Convert MEM0_API_KEY to api.key
                config_key = key[len(self.prefix):].lower().replace("_", ".")
                
                # Try to parse JSON values
                try:
                    config[config_key] = json.loads(value)
                except json.JSONDecodeError:
                    config[config_key] = value
                    
        return self._unflatten_dict(config)
        
    async def save(self, config: Dict[str, Any]) -> None:
        """Cannot save to environment"""
        raise NotImplementedError("Cannot save configuration to environment variables")
        
    def get_priority(self) -> int:
        return 10  # High priority
        
    def _unflatten_dict(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert flat.key.notation to nested dict"""
        result = {}
        
        for key, value in flat_dict.items():
            parts = key.split(".")
            current = result
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
                
            current[parts[-1]] = value
            
        return result


class FileConfigSource(ConfigSource):
    """Load configuration from file (JSON/YAML)"""
    
    def __init__(self, file_path: Union[str, Path], auto_reload: bool = False):
        self.file_path = Path(file_path)
        self.auto_reload = auto_reload
        self._last_modified: Optional[float] = None
        self._watcher_task: Optional[asyncio.Task] = None
        
    async def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.file_path.exists():
            logger.warning(f"Configuration file not found: {self.file_path}")
            return {}
            
        with open(self.file_path, "r") as f:
            if self.file_path.suffix in [".yaml", ".yml"]:
                config = yaml.safe_load(f) or {}
            else:
                config = json.load(f)
                
        self._last_modified = self.file_path.stat().st_mtime
        
        if self.auto_reload and not self._watcher_task:
            self._watcher_task = asyncio.create_task(self._watch_file())
            
        return config
        
    async def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.file_path, "w") as f:
            if self.file_path.suffix in [".yaml", ".yml"]:
                yaml.safe_dump(config, f, default_flow_style=False)
            else:
                json.dump(config, f, indent=2)
                
        self._last_modified = self.file_path.stat().st_mtime
        
    def get_priority(self) -> int:
        return 50  # Medium priority
        
    async def _watch_file(self) -> None:
        """Watch file for changes"""
        while self.auto_reload:
            try:
                await asyncio.sleep(1)
                
                if self.file_path.exists():
                    mtime = self.file_path.stat().st_mtime
                    if mtime != self._last_modified:
                        logger.info(f"Configuration file changed: {self.file_path}")
                        # Trigger reload via event
                        # This would be handled by ConfigManager
                        
            except Exception as e:
                logger.error(f"Error watching config file: {e}")


class RemoteConfigSource(ConfigSource):
    """Load configuration from remote source (e.g., API, etcd, consul)"""
    
    def __init__(self, url: str, auth_token: Optional[str] = None):
        self.url = url
        self.auth_token = auth_token
        
    async def load(self) -> Dict[str, Any]:
        """Load configuration from remote source"""
        # Implementation would use httpx or similar
        # This is a placeholder
        return {}
        
    async def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to remote source"""
        # Implementation would use httpx or similar
        pass
        
    def get_priority(self) -> int:
        return 30  # Higher than file, lower than env


@dataclass
class ConfigSchema:
    """Schema definition for configuration validation"""
    name: str
    type: Type
    required: bool = True
    default: Any = None
    description: str = ""
    validator: Optional[callable] = None
    children: Dict[str, 'ConfigSchema'] = field(default_factory=dict)


class ConfigManager:
    """
    Central configuration management system.
    
    Features:
    - Multiple configuration sources with priority
    - Schema validation
    - Dynamic configuration updates
    - Configuration templating
    - Secret management
    """
    
    def __init__(self):
        self._sources: List[ConfigSource] = []
        self._config: Dict[str, Any] = {}
        self._schema: Dict[str, ConfigSchema] = {}
        self._listeners: List[callable] = []
        self._secrets: Dict[str, str] = {}
        self._loaded = False
        
    def add_source(self, source: ConfigSource) -> None:
        """Add a configuration source"""
        self._sources.append(source)
        # Sort by priority
        self._sources.sort(key=lambda s: s.get_priority())
        
    def define_schema(self, schema: Dict[str, ConfigSchema]) -> None:
        """Define configuration schema"""
        self._schema = schema
        
    async def load(self) -> None:
        """Load configuration from all sources"""
        logger.info("Loading configuration...")
        
        # Start with empty config
        merged_config = {}
        
        # Load from sources in reverse priority order
        # (so higher priority sources override)
        for source in reversed(self._sources):
            try:
                config = await source.load()
                merged_config = self._deep_merge(merged_config, config)
            except Exception as e:
                logger.error(f"Failed to load config from {source.__class__.__name__}: {e}")
                
        # Apply templates
        self._config = self._apply_templates(merged_config)
        
        # Validate against schema
        if self._schema:
            self._validate_config()
            
        # Decrypt secrets
        self._decrypt_secrets()
        
        self._loaded = True
        
        # Notify listeners
        await self._notify_listeners()
        
        logger.info("Configuration loaded successfully")
        
    async def reload(self) -> None:
        """Reload configuration from all sources"""
        await self.load()
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Supports dot notation: config.get("api.key")
        """
        parts = key.split(".")
        value = self._config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        This only updates the runtime configuration.
        Use save() to persist changes.
        """
        parts = key.split(".")
        config = self._config
        
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
            
        config[parts[-1]] = value
        
        # Notify listeners
        asyncio.create_task(self._notify_listeners())
        
    async def save(self, source_index: int = 0) -> None:
        """Save configuration to a specific source"""
        if source_index >= len(self._sources):
            raise ValueError(f"Invalid source index: {source_index}")
            
        source = self._sources[source_index]
        await source.save(self._config)
        
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration"""
        return self._config.copy()
        
    def add_listener(self, listener: callable) -> None:
        """Add configuration change listener"""
        self._listeners.append(listener)
        
    def remove_listener(self, listener: callable) -> bool:
        """Remove configuration change listener"""
        try:
            self._listeners.remove(listener)
            return True
        except ValueError:
            return False
            
    async def _notify_listeners(self) -> None:
        """Notify all listeners of configuration change"""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(self._config)
                else:
                    listener(self._config)
            except Exception as e:
                logger.error(f"Error in config listener: {e}")
                
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def _apply_templates(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply template substitution to configuration values"""
        import re
        
        def substitute(value: Any) -> Any:
            if isinstance(value, str):
                # Replace ${VAR} with environment variable
                pattern = re.compile(r'\$\{([^}]+)\}')
                
                def replacer(match):
                    var_name = match.group(1)
                    # Check environment
                    if var_name in os.environ:
                        return os.environ[var_name]
                    # Check config itself
                    elif ":" in var_name:
                        config_key, default = var_name.split(":", 1)
                        return str(self.get(config_key, default))
                    else:
                        return str(self.get(var_name, match.group(0)))
                        
                return pattern.sub(replacer, value)
                
            elif isinstance(value, dict):
                return {k: substitute(v) for k, v in value.items()}
                
            elif isinstance(value, list):
                return [substitute(v) for v in value]
                
            return value
            
        return substitute(config)
        
    def _validate_config(self) -> None:
        """Validate configuration against schema"""
        # TODO: Implement schema validation
        pass
        
    def _decrypt_secrets(self) -> None:
        """Decrypt any encrypted configuration values"""
        # TODO: Implement secret decryption
        pass
        
    def register_secret(self, key: str, encrypted_value: str) -> None:
        """Register an encrypted secret"""
        self._secrets[key] = encrypted_value
        
    def get_secret(self, key: str) -> Optional[str]:
        """Get decrypted secret value"""
        if key in self._secrets:
            # TODO: Implement decryption
            return self._secrets[key]
        return None


# Default configuration schema
DEFAULT_SCHEMA = {
    "api": ConfigSchema(
        name="api",
        type=dict,
        description="API configuration",
        children={
            "key": ConfigSchema(
                name="key",
                type=str,
                required=True,
                description="Mem0 API key"
            ),
            "host": ConfigSchema(
                name="host",
                type=str,
                default="https://api.mem0.ai",
                description="Mem0 API host"
            ),
            "timeout": ConfigSchema(
                name="timeout",
                type=int,
                default=30,
                description="API request timeout in seconds"
            )
        }
    ),
    "defaults": ConfigSchema(
        name="defaults",
        type=dict,
        description="Default values",
        children={
            "user_id": ConfigSchema(
                name="user_id",
                type=str,
                required=False,
                description="Default user ID"
            ),
            "page_size": ConfigSchema(
                name="page_size",
                type=int,
                default=100,
                description="Default page size for list operations"
            )
        }
    ),
    "features": ConfigSchema(
        name="features",
        type=dict,
        description="Feature flags",
        children={
            "graph_memory": ConfigSchema(
                name="graph_memory",
                type=bool,
                default=False,
                description="Enable graph memory"
            ),
            "multimodal": ConfigSchema(
                name="multimodal",
                type=bool,
                default=True,
                description="Enable multimodal support"
            )
        }
    )
}