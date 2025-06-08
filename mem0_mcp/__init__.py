"""
Mem0 MCP Server - Extensible Architecture

This package provides a Model Context Protocol (MCP) server for Mem0 with an
extensible plugin architecture supporting:
- Plugin-based operation handlers
- Custom entity types
- Pluggable graph backends
- Custom export format handlers
- Dynamic configuration loading
- Event hooks and middleware
- Dependency injection
"""

__version__ = "0.2.0"
__all__ = [
    "Mem0MCPServer",
    "PluginRegistry",
    "BasePlugin",
    "BaseOperationHandler",
    "ConfigManager",
    "EventBus",
]

from .core.server import Mem0MCPServer
from .core.plugin_registry import PluginRegistry
from .core.base_plugin import BasePlugin
from .core.base_operation import BaseOperationHandler
from .core.config_manager import ConfigManager
from .core.event_bus import EventBus