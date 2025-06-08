"""
Base Plugin Architecture

Provides the foundation for creating extensible plugins that can be loaded
dynamically into the Mem0 MCP Server.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    name: str
    version: str
    description: str
    author: Optional[str] = None
    dependencies: List[str] = None
    capabilities: List[str] = None
    config_schema: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.capabilities is None:
            self.capabilities = []


class PluginLifecycle(ABC):
    """Defines the lifecycle hooks for plugins"""
    
    async def on_load(self) -> None:
        """Called when the plugin is loaded"""
        pass
    
    async def on_start(self) -> None:
        """Called when the server starts"""
        pass
    
    async def on_stop(self) -> None:
        """Called when the server stops"""
        pass
    
    async def on_unload(self) -> None:
        """Called when the plugin is unloaded"""
        pass


class BasePlugin(PluginLifecycle):
    """
    Base class for all plugins in the Mem0 MCP Server.
    
    Plugins can extend functionality by:
    1. Adding new operations to existing tools
    2. Adding new tools entirely
    3. Providing new backends (e.g., graph stores, vector stores)
    4. Adding middleware for request/response processing
    5. Extending configuration options
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._metadata: Optional[PluginMetadata] = None
        self._initialized = False
        
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    async def initialize(self) -> None:
        """Initialize the plugin with its configuration"""
        if self._initialized:
            return
            
        await self.validate_config()
        await self.setup()
        self._initialized = True
        
    async def validate_config(self) -> None:
        """Validate plugin configuration against schema"""
        if self.metadata.config_schema:
            # TODO: Implement JSON schema validation
            pass
    
    @abstractmethod
    async def setup(self) -> None:
        """Setup plugin resources"""
        pass
    
    async def teardown(self) -> None:
        """Cleanup plugin resources"""
        pass
    
    def get_capability(self, capability: str) -> bool:
        """Check if plugin provides a specific capability"""
        return capability in self.metadata.capabilities


class OperationPlugin(BasePlugin):
    """Base class for plugins that add operations to existing tools"""
    
    @abstractmethod
    def get_operations(self) -> Dict[str, 'BaseOperationHandler']:
        """Return a mapping of operation names to handlers"""
        pass
    
    @abstractmethod
    def get_tool_name(self) -> str:
        """Return the name of the tool this plugin extends"""
        pass


class ToolPlugin(BasePlugin):
    """Base class for plugins that add entirely new tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return the MCP tool definition"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass


class BackendPlugin(BasePlugin, Generic[T]):
    """Base class for plugins that provide backend implementations"""
    
    @abstractmethod
    def get_backend_type(self) -> str:
        """Return the type of backend (e.g., 'graph', 'vector', 'storage')"""
        pass
    
    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend implementation"""
        pass
    
    @abstractmethod
    def create_client(self, **kwargs) -> T:
        """Create and return a client instance"""
        pass


class MiddlewarePlugin(BasePlugin):
    """Base class for plugins that act as middleware"""
    
    @abstractmethod
    async def process_request(self, tool_name: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request before execution"""
        return params
    
    @abstractmethod
    async def process_response(self, tool_name: str, operation: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process response before returning to client"""
        return response
    
    @abstractmethod
    def get_priority(self) -> int:
        """Return middleware priority (lower executes first)"""
        return 100


class ExtensionPlugin(BasePlugin):
    """Base class for general extension plugins"""
    
    @abstractmethod
    def extend(self, server: 'Mem0MCPServer') -> None:
        """
        Extend the server with custom functionality.
        This method has access to the full server instance.
        """
        pass


class CompositePlugin(BasePlugin):
    """Plugin that can contain multiple sub-plugins"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._plugins: List[BasePlugin] = []
        
    def add_plugin(self, plugin: BasePlugin) -> None:
        """Add a sub-plugin"""
        self._plugins.append(plugin)
        
    async def setup(self) -> None:
        """Setup all sub-plugins"""
        for plugin in self._plugins:
            await plugin.initialize()
            
    async def teardown(self) -> None:
        """Teardown all sub-plugins"""
        for plugin in reversed(self._plugins):
            await plugin.teardown()
            
    def get_plugins(self, plugin_type: Type[T]) -> List[T]:
        """Get all sub-plugins of a specific type"""
        return [p for p in self._plugins if isinstance(p, plugin_type)]