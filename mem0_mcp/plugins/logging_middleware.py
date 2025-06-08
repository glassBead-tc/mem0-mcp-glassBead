"""
Logging Middleware Plugin

Demonstrates middleware plugin that logs all tool operations.
"""

import logging
import time
from typing import Any, Dict
from ..core.base_plugin import MiddlewarePlugin, PluginMetadata

logger = logging.getLogger(__name__)


class LoggingMiddlewarePlugin(MiddlewarePlugin):
    """Middleware that logs all tool operations"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="logging_middleware",
            version="1.0.0",
            description="Logs all tool operations for debugging and monitoring",
            author="Mem0 Team",
            capabilities=["logging", "monitoring"]
        )
        
    async def setup(self) -> None:
        """Setup logging configuration"""
        log_level = self.config.get("log_level", "INFO")
        logger.setLevel(getattr(logging, log_level))
        logger.info(f"Logging middleware initialized with level: {log_level}")
        
    async def process_request(self, tool_name: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Log incoming requests"""
        # Add request timestamp
        params["_request_time"] = time.time()
        
        # Log request
        logger.info(f"Request: {tool_name}.{operation}", extra={
            "tool": tool_name,
            "operation": operation,
            "params": self._sanitize_params(params)
        })
        
        return params
        
    async def process_response(self, tool_name: str, operation: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Log responses and timing"""
        # Calculate execution time
        request_time = response.pop("_request_time", None)
        if request_time:
            execution_time = time.time() - request_time
            response["_execution_time_ms"] = int(execution_time * 1000)
            
        # Log response
        status = response.get("status", "unknown")
        log_method = logger.info if status == "success" else logger.error
        
        log_method(f"Response: {tool_name}.{operation} - {status}", extra={
            "tool": tool_name,
            "operation": operation,
            "status": status,
            "execution_time_ms": response.get("_execution_time_ms"),
            "error": response.get("error") if status != "success" else None
        })
        
        return response
        
    def get_priority(self) -> int:
        """High priority to log before other middleware"""
        return 10
        
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from params"""
        sanitized = params.copy()
        
        # Remove sensitive fields
        sensitive_fields = ["api_key", "password", "token", "secret"]
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***REDACTED***"
                
        return sanitized