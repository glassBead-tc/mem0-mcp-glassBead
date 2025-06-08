"""
Cache Plugin

Provides caching capabilities for memory operations.
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, Optional
from ..core.base_plugin import MiddlewarePlugin, PluginMetadata

class CachePlugin(MiddlewarePlugin):
    """Middleware that caches memory operation results"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="cache_plugin",
            version="1.0.0",
            description="Provides caching for memory operations to improve performance",
            author="Mem0 Team",
            capabilities=["caching", "performance"],
            config_schema={
                "ttl": {"type": "integer", "default": 300},
                "max_size": {"type": "integer", "default": 1000},
                "cacheable_operations": {
                    "type": "array",
                    "default": ["search", "get", "get_all"]
                }
            }
        )
        
    async def setup(self) -> None:
        """Initialize cache"""
        self.cache: Dict[str, tuple[float, Any]] = {}
        self.ttl = self.config.get("ttl", 300)
        self.max_size = self.config.get("max_size", 1000)
        self.cacheable_operations = set(self.config.get("cacheable_operations", ["search", "get", "get_all"]))
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    async def teardown(self) -> None:
        """Cleanup resources"""
        if hasattr(self, "cleanup_task"):
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
                
    async def process_request(self, tool_name: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check cache for cached results"""
        if operation not in self.cacheable_operations:
            return params
            
        cache_key = self._get_cache_key(tool_name, operation, params)
        
        # Check cache
        if cache_key in self.cache:
            timestamp, cached_result = self.cache[cache_key]
            if asyncio.get_event_loop().time() - timestamp < self.ttl:
                # Return cached result
                params["_cached_result"] = cached_result
                params["_from_cache"] = True
                
        params["_cache_key"] = cache_key
        return params
        
    async def process_response(self, tool_name: str, operation: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """Cache successful responses"""
        # If result was from cache, return it
        if response.get("_from_cache"):
            cached_result = response.pop("_cached_result")
            response.pop("_from_cache")
            response.pop("_cache_key", None)
            return {**cached_result, "_cached": True}
            
        # Cache new results
        if operation in self.cacheable_operations and response.get("status") == "success":
            cache_key = response.pop("_cache_key", None)
            if cache_key:
                # Ensure cache size limit
                if len(self.cache) >= self.max_size:
                    # Remove oldest entry
                    oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
                    del self.cache[oldest_key]
                    
                # Cache result
                self.cache[cache_key] = (asyncio.get_event_loop().time(), response.copy())
                
        return response
        
    def get_priority(self) -> int:
        """Medium priority"""
        return 50
        
    def _get_cache_key(self, tool_name: str, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        # Remove non-deterministic fields
        cache_params = {k: v for k, v in params.items() 
                       if not k.startswith("_") and k not in ["session_id"]}
        
        cache_data = {
            "tool": tool_name,
            "operation": operation,
            "params": cache_params
        }
        
        # Generate hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
        
    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = asyncio.get_event_loop().time()
                expired_keys = [
                    key for key, (timestamp, _) in self.cache.items()
                    if current_time - timestamp > self.ttl
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                    
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Continue cleanup loop