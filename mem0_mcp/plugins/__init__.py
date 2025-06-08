"""
Built-in Plugins for Mem0 MCP Server

This package contains built-in plugins that demonstrate the extensibility
of the Mem0 MCP Server architecture.
"""

from typing import List, Type
from ..core.base_plugin import BasePlugin

# Import built-in plugins
from .logging_middleware import LoggingMiddlewarePlugin
from .cache_plugin import CachePlugin
from .neo4j_backend import Neo4jBackendPlugin
from .batch_operations import BatchOperationsPlugin
from .feedback_operations import FeedbackOperationsPlugin
from .history_operations import HistoryOperationsPlugin


def get_builtin_plugins() -> List[Type[BasePlugin]]:
    """Get list of built-in plugin classes"""
    return [
        LoggingMiddlewarePlugin,
        CachePlugin,
        Neo4jBackendPlugin,
        BatchOperationsPlugin,
        FeedbackOperationsPlugin,
        HistoryOperationsPlugin
    ]