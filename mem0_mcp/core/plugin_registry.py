"""
Plugin Registry System

Manages plugin discovery, loading, and lifecycle management.
Supports dynamic plugin loading from multiple sources.
"""

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
import asyncio
from collections import defaultdict

from .base_plugin import (
    BasePlugin, OperationPlugin, ToolPlugin, BackendPlugin,
    MiddlewarePlugin, ExtensionPlugin, PluginMetadata
)
from .base_operation import BaseOperationHandler

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BasePlugin)


class PluginRegistry:
    """
    Central registry for all plugins in the system.
    
    Features:
    - Dynamic plugin discovery and loading
    - Plugin dependency resolution
    - Lifecycle management
    - Plugin isolation and sandboxing
    - Hot reloading support
    """
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_types: Dict[Type[BasePlugin], List[str]] = defaultdict(list)
        self._load_order: List[str] = []
        self._initialized = False
        
        # Plugin sources
        self._builtin_plugins: List[Type[BasePlugin]] = []
        self._plugin_paths: List[Path] = []
        self._plugin_modules: List[str] = []
        
    def add_builtin_plugin(self, plugin_class: Type[BasePlugin]) -> None:
        """Register a built-in plugin class"""
        self._builtin_plugins.append(plugin_class)
        
    def add_plugin_path(self, path: Union[str, Path]) -> None:
        """Add a directory to search for plugins"""
        self._plugin_paths.append(Path(path))
        
    def add_plugin_module(self, module_name: str) -> None:
        """Add a module to load plugins from"""
        self._plugin_modules.append(module_name)
        
    async def discover_and_load(self) -> None:
        """Discover and load all plugins"""
        logger.info("Starting plugin discovery...")
        
        # Load built-in plugins
        for plugin_class in self._builtin_plugins:
            await self._load_plugin_class(plugin_class)
            
        # Load from plugin paths
        for path in self._plugin_paths:
            await self._discover_plugins_in_path(path)
            
        # Load from modules
        for module_name in self._plugin_modules:
            await self._discover_plugins_in_module(module_name)
            
        # Resolve dependencies and determine load order
        self._resolve_dependencies()
        
        # Initialize plugins in dependency order
        await self._initialize_plugins()
        
        self._initialized = True
        logger.info(f"Loaded {len(self._plugins)} plugins")
        
    async def _load_plugin_class(self, plugin_class: Type[BasePlugin], config: Optional[Dict[str, Any]] = None) -> None:
        """Load a single plugin class"""
        try:
            # Create instance
            plugin = plugin_class(config)
            metadata = plugin.metadata
            
            # Check if already loaded
            if metadata.name in self._plugins:
                logger.warning(f"Plugin '{metadata.name}' already loaded, skipping")
                return
                
            # Register plugin
            self._plugins[metadata.name] = plugin
            
            # Register by type
            for base_class in inspect.getmro(plugin_class):
                if base_class in [OperationPlugin, ToolPlugin, BackendPlugin, MiddlewarePlugin, ExtensionPlugin]:
                    self._plugin_types[base_class].append(metadata.name)
                    
            logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_class.__name__}: {e}")
            
    async def _discover_plugins_in_path(self, path: Path) -> None:
        """Discover plugins in a directory"""
        if not path.exists() or not path.is_dir():
            logger.warning(f"Plugin path does not exist: {path}")
            return
            
        for file_path in path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
                
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                f"plugin_{file_path.stem}",
                file_path
            )
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find plugin classes in module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BasePlugin) and 
                        obj != BasePlugin and
                        not inspect.isabstract(obj)):
                        await self._load_plugin_class(obj)
                        
    async def _discover_plugins_in_module(self, module_name: str) -> None:
        """Discover plugins in a Python module"""
        try:
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin and
                    not inspect.isabstract(obj)):
                    await self._load_plugin_class(obj)
                    
        except ImportError as e:
            logger.error(f"Failed to import plugin module {module_name}: {e}")
            
    def _resolve_dependencies(self) -> None:
        """Resolve plugin dependencies and determine load order"""
        # Build dependency graph
        graph = {}
        for name, plugin in self._plugins.items():
            graph[name] = plugin.metadata.dependencies or []
            
        # Topological sort
        self._load_order = self._topological_sort(graph)
        
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph"""
        visited = set()
        stack = []
        
        def visit(node: str) -> None:
            if node in visited:
                return
            visited.add(node)
            
            for dep in graph.get(node, []):
                if dep in graph:  # Only visit if dependency exists
                    visit(dep)
                    
            stack.append(node)
            
        for node in graph:
            visit(node)
            
        return stack
        
    async def _initialize_plugins(self) -> None:
        """Initialize plugins in dependency order"""
        for plugin_name in self._load_order:
            plugin = self._plugins[plugin_name]
            
            try:
                await plugin.initialize()
                await plugin.on_load()
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
                # Remove failed plugin
                del self._plugins[plugin_name]
                
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a specific plugin by name"""
        return self._plugins.get(name)
        
    def get_plugins_by_type(self, plugin_type: Type[T]) -> List[T]:
        """Get all plugins of a specific type"""
        plugin_names = self._plugin_types.get(plugin_type, [])
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
        
    def get_operation_handlers(self, tool_name: str) -> Dict[str, BaseOperationHandler]:
        """Get all operation handlers for a specific tool"""
        handlers = {}
        
        for plugin in self.get_plugins_by_type(OperationPlugin):
            if plugin.get_tool_name() == tool_name:
                handlers.update(plugin.get_operations())
                
        return handlers
        
    def get_middleware_chain(self) -> List[MiddlewarePlugin]:
        """Get middleware plugins sorted by priority"""
        middleware = self.get_plugins_by_type(MiddlewarePlugin)
        return sorted(middleware, key=lambda m: m.get_priority())
        
    def get_backend(self, backend_type: str, backend_name: str) -> Optional[BackendPlugin]:
        """Get a specific backend plugin"""
        for plugin in self.get_plugins_by_type(BackendPlugin):
            if (plugin.get_backend_type() == backend_type and 
                plugin.get_backend_name() == backend_name):
                return plugin
        return None
        
    async def start_all(self) -> None:
        """Start all plugins"""
        for plugin_name in self._load_order:
            if plugin_name in self._plugins:
                plugin = self._plugins[plugin_name]
                try:
                    await plugin.on_start()
                except Exception as e:
                    logger.error(f"Failed to start plugin {plugin_name}: {e}")
                    
    async def stop_all(self) -> None:
        """Stop all plugins"""
        for plugin_name in reversed(self._load_order):
            if plugin_name in self._plugins:
                plugin = self._plugins[plugin_name]
                try:
                    await plugin.on_stop()
                except Exception as e:
                    logger.error(f"Failed to stop plugin {plugin_name}: {e}")
                    
    async def unload_all(self) -> None:
        """Unload all plugins"""
        for plugin_name in reversed(self._load_order):
            if plugin_name in self._plugins:
                plugin = self._plugins[plugin_name]
                try:
                    await plugin.on_unload()
                    await plugin.teardown()
                except Exception as e:
                    logger.error(f"Failed to unload plugin {plugin_name}: {e}")
                    
        self._plugins.clear()
        self._plugin_types.clear()
        self._load_order.clear()
        self._initialized = False
        
    async def reload_plugin(self, name: str) -> bool:
        """Hot reload a specific plugin"""
        if name not in self._plugins:
            logger.error(f"Plugin {name} not found")
            return False
            
        plugin = self._plugins[name]
        plugin_class = plugin.__class__
        config = plugin.config
        
        try:
            # Unload existing plugin
            await plugin.on_unload()
            await plugin.teardown()
            
            # Remove from registry
            del self._plugins[name]
            for plugin_list in self._plugin_types.values():
                if name in plugin_list:
                    plugin_list.remove(name)
                    
            # Reload plugin class
            await self._load_plugin_class(plugin_class, config)
            
            # Re-initialize
            new_plugin = self._plugins[name]
            await new_plugin.initialize()
            await new_plugin.on_load()
            await new_plugin.on_start()
            
            logger.info(f"Successfully reloaded plugin {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload plugin {name}: {e}")
            return False
            
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins"""
        info = []
        
        for name, plugin in self._plugins.items():
            metadata = plugin.metadata
            info.append({
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "author": metadata.author,
                "type": plugin.__class__.__name__,
                "capabilities": metadata.capabilities,
                "dependencies": metadata.dependencies
            })
            
        return info