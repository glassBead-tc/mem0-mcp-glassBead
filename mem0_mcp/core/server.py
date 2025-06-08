"""
Main Mem0 MCP Server Implementation

Provides the core server with extensible architecture supporting:
- Plugin-based operations
- Dynamic tool registration
- Event-driven architecture
- Dependency injection
- Configuration management
"""

import logging
from typing import Any, Dict, List, Optional, Type
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mem0 import MemoryClient, AsyncMemoryClient

from .plugin_registry import PluginRegistry
from .config_manager import ConfigManager, EnvConfigSource, FileConfigSource
from .event_bus import EventBus, Event
from .dependency_injection import Container, ServiceProvider
from .base_plugin import BasePlugin, ToolPlugin, ExtensionPlugin
from .base_operation import OperationContext

logger = logging.getLogger(__name__)


class Mem0MCPServer:
    """
    Main server class for the Mem0 MCP implementation.
    
    Features:
    - Extensible plugin architecture
    - Dynamic tool registration
    - Event-driven communication
    - Flexible configuration
    - Dependency injection
    """
    
    def __init__(self, name: str = "mem0-mcp", config_path: Optional[str] = None):
        self.name = name
        self.mcp = FastMCP(name)
        
        # Core components
        self.plugin_registry = PluginRegistry()
        self.config_manager = ConfigManager()
        self.event_bus = EventBus()
        self.container = Container()
        self.service_provider = ServiceProvider(self.container)
        
        # Clients
        self.sync_client: Optional[MemoryClient] = None
        self.async_client: Optional[AsyncMemoryClient] = None
        
        # Tool handlers
        self._tool_handlers: Dict[str, callable] = {}
        
        # Initialize configuration
        self._setup_configuration(config_path)
        
        # Register core services
        self._register_core_services()
        
    def _setup_configuration(self, config_path: Optional[str] = None) -> None:
        """Setup configuration sources"""
        # Add environment source
        self.config_manager.add_source(EnvConfigSource("MEM0_"))
        
        # Add file source if provided
        if config_path:
            self.config_manager.add_source(FileConfigSource(config_path))
            
        # Add default configuration file if exists
        from pathlib import Path
        default_config = Path("mem0-config.yaml")
        if default_config.exists():
            self.config_manager.add_source(FileConfigSource(default_config))
            
    def _register_core_services(self) -> None:
        """Register core services in DI container"""
        self.container.register_instance(Mem0MCPServer, self)
        self.container.register_instance(PluginRegistry, self.plugin_registry)
        self.container.register_instance(ConfigManager, self.config_manager)
        self.container.register_instance(EventBus, self.event_bus)
        self.container.register_instance(FastMCP, self.mcp)
        
    async def initialize(self) -> None:
        """Initialize the server and all components"""
        logger.info(f"Initializing {self.name} server...")
        
        # Load configuration
        await self.config_manager.load()
        
        # Initialize clients
        await self._initialize_clients()
        
        # Register clients in DI container
        if self.sync_client:
            self.container.register_instance(MemoryClient, self.sync_client)
        if self.async_client:
            self.container.register_instance(AsyncMemoryClient, self.async_client)
        
        # Discover and load plugins
        await self._load_plugins()
        
        # Register tools
        await self._register_tools()
        
        # Start event bus
        await self.event_bus.start()
        
        # Emit initialization event
        await self.event_bus.emit("server.initialized", {
            "name": self.name,
            "plugins": self.plugin_registry.get_plugin_info()
        })
        
        logger.info(f"{self.name} server initialized successfully")
        
    async def _initialize_clients(self) -> None:
        """Initialize Mem0 clients"""
        api_key = self.config_manager.get("api.key")
        if not api_key:
            raise ValueError("MEM0_API_KEY not found in configuration")
            
        host = self.config_manager.get("api.host", "https://api.mem0.ai")
        org_id = self.config_manager.get("organization.org_id")
        project_id = self.config_manager.get("organization.project_id")
        
        # Initialize sync client
        self.sync_client = MemoryClient(
            api_key=api_key,
            host=host,
            org_id=org_id,
            project_id=project_id
        )
        
        # Initialize async client if enabled
        if self.config_manager.get("performance.use_async", True):
            self.async_client = AsyncMemoryClient(
                api_key=api_key,
                host=host,
                org_id=org_id,
                project_id=project_id
            )
            
        # Set custom instructions if provided
        custom_instructions = self.config_manager.get("defaults.custom_instructions")
        if custom_instructions and self.sync_client:
            self.sync_client.update_project(custom_instructions=custom_instructions)
            
    async def _load_plugins(self) -> None:
        """Load all plugins"""
        # Add built-in plugins
        from ..plugins import get_builtin_plugins
        for plugin_class in get_builtin_plugins():
            self.plugin_registry.add_builtin_plugin(plugin_class)
            
        # Add plugin paths from config
        plugin_paths = self.config_manager.get("plugins.paths", [])
        for path in plugin_paths:
            self.plugin_registry.add_plugin_path(path)
            
        # Add plugin modules from config
        plugin_modules = self.config_manager.get("plugins.modules", [])
        for module in plugin_modules:
            self.plugin_registry.add_plugin_module(module)
            
        # Discover and load all plugins
        await self.plugin_registry.discover_and_load()
        
        # Let extension plugins extend the server
        for plugin in self.plugin_registry.get_plugins_by_type(ExtensionPlugin):
            plugin.extend(self)
            
    async def _register_tools(self) -> None:
        """Register all tools from plugins"""
        # Register tools from ToolPlugin instances
        for plugin in self.plugin_registry.get_plugins_by_type(ToolPlugin):
            await self._register_tool_plugin(plugin)
            
        # Register the 7 main tools with operation routing
        await self._register_main_tools()
        
    async def _register_tool_plugin(self, plugin: ToolPlugin) -> None:
        """Register a tool from a plugin"""
        tool_def = plugin.get_tool_definition()
        tool_name = tool_def["name"]
        
        # Create handler function
        async def tool_handler(**kwargs):
            context = OperationContext(
                tool_name=tool_name,
                operation_name="execute",
                user_id=kwargs.get("user_id"),
                session_id=kwargs.get("session_id")
            )
            
            # Apply middleware
            for middleware in self.plugin_registry.get_middleware_chain():
                kwargs = await middleware.process_request(tool_name, "execute", kwargs)
                
            # Execute tool
            result = await plugin.execute(**kwargs)
            
            # Apply middleware to response
            for middleware in reversed(self.plugin_registry.get_middleware_chain()):
                result = await middleware.process_response(tool_name, "execute", result)
                
            return result
            
        # Register with MCP
        self.mcp.tool(
            description=tool_def.get("description", "")
        )(tool_handler)
        
        # Store handler reference
        self._tool_handlers[tool_name] = tool_handler
        
        logger.info(f"Registered tool: {tool_name}")
        
    async def _register_main_tools(self) -> None:
        """Register the 7 main tools with operation routing"""
        # Import tool implementations
        from ..tools import (
            mem0_memory, mem0_entity, mem0_graph, mem0_export,
            mem0_config, mem0_webhook, mem0_advanced
        )
        
        tools = [
            mem0_memory, mem0_entity, mem0_graph, mem0_export,
            mem0_config, mem0_webhook, mem0_advanced
        ]
        
        for tool_module in tools:
            await self._register_tool_with_operations(tool_module)
            
    async def _register_tool_with_operations(self, tool_module) -> None:
        """Register a tool that supports multiple operations"""
        tool_name = tool_module.TOOL_NAME
        tool_description = tool_module.TOOL_DESCRIPTION
        tool_parameters = tool_module.TOOL_PARAMETERS
        
        # Get operation handlers from plugins
        operation_handlers = self.plugin_registry.get_operation_handlers(tool_name)
        
        # Add built-in operations
        if hasattr(tool_module, "get_builtin_operations"):
            builtin_ops = tool_module.get_builtin_operations()
            operation_handlers.update(builtin_ops)
            
        # Create main tool handler
        async def tool_handler(**kwargs):
            operation = kwargs.get("operation")
            if not operation:
                return {"error": "Operation parameter is required"}
                
            if operation not in operation_handlers:
                return {"error": f"Unknown operation: {operation}"}
                
            # Create context
            context = OperationContext(
                tool_name=tool_name,
                operation_name=operation,
                user_id=kwargs.get("user_id"),
                session_id=kwargs.get("session_id")
            )
            
            # Apply middleware
            for middleware in self.plugin_registry.get_middleware_chain():
                kwargs = await middleware.process_request(tool_name, operation, kwargs)
                
            # Get handler
            handler = operation_handlers[operation]
            
            # Execute operation
            result = await handler(context, **kwargs)
            
            # Apply middleware to response
            for middleware in reversed(self.plugin_registry.get_middleware_chain()):
                result = await middleware.process_response(tool_name, operation, result)
                
            # Emit event
            await self.event_bus.emit(f"tool.{tool_name}.{operation}", {
                "params": kwargs,
                "result": result,
                "context": context
            })
            
            return result
            
        # Set function name to avoid MCP warnings
        tool_handler.__name__ = f"{tool_name}_handler"
        
        # Register with MCP
        self.mcp.tool(
            description=tool_description
        )(tool_handler)
        
        # Store handler reference
        self._tool_handlers[tool_name] = tool_handler
        
        logger.info(f"Registered tool: {tool_name} with {len(operation_handlers)} operations")
        
    async def start(self) -> None:
        """Start the server"""
        logger.info(f"Starting {self.name} server...")
        
        # Start all plugins
        await self.plugin_registry.start_all()
        
        # Emit start event
        await self.event_bus.emit("server.started", {"name": self.name})
        
        logger.info(f"{self.name} server started")
        
    async def stop(self) -> None:
        """Stop the server"""
        logger.info(f"Stopping {self.name} server...")
        
        # Emit stop event
        await self.event_bus.emit("server.stopping", {"name": self.name})
        
        # Stop all plugins
        await self.plugin_registry.stop_all()
        
        # Stop event bus
        await self.event_bus.stop()
        
        logger.info(f"{self.name} server stopped")
        
    async def shutdown(self) -> None:
        """Shutdown the server and cleanup resources"""
        await self.stop()
        
        # Unload all plugins
        await self.plugin_registry.unload_all()
        
        # Close clients if they have a close method
        if self.async_client and hasattr(self.async_client, 'close'):
            await self.async_client.close()
            
    def get_mcp_server(self) -> Server:
        """Get the underlying MCP server instance"""
        return self.mcp._mcp_server
        
    def add_plugin(self, plugin: BasePlugin) -> None:
        """Add a plugin at runtime"""
        self.plugin_registry._builtin_plugins.append(plugin.__class__)
        
    def register_event_handler(self, event_name: str, handler: callable) -> None:
        """Register an event handler"""
        self.event_bus.subscribe(event_name, handler)
        
    def get_service(self, service_type: Type) -> Any:
        """Get a service from the DI container"""
        return asyncio.run(self.container.resolve(service_type))