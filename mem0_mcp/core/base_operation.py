"""
Base Operation Handler Architecture

Provides the foundation for implementing operation handlers that can be
dynamically loaded and executed by tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict, Union, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field
import inspect
import asyncio
from enum import Enum

class ParameterType(Enum):
    """Supported parameter types for operations"""
    STRING = "string"
    INTEGER = "integer" 
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    ANY = "any"


@dataclass
class ParameterDefinition:
    """Defines a parameter for an operation"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None
    validation: Optional[Callable[[Any], bool]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value"""
        if value is None:
            return not self.required
            
        if self.choices and value not in self.choices:
            return False
            
        if self.validation:
            return self.validation(value)
            
        # Type validation
        type_validators = {
            ParameterType.STRING: lambda v: isinstance(v, str),
            ParameterType.INTEGER: lambda v: isinstance(v, int),
            ParameterType.FLOAT: lambda v: isinstance(v, (int, float)),
            ParameterType.BOOLEAN: lambda v: isinstance(v, bool),
            ParameterType.OBJECT: lambda v: isinstance(v, dict),
            ParameterType.ARRAY: lambda v: isinstance(v, list),
            ParameterType.ANY: lambda v: True
        }
        
        return type_validators[self.type](value)


@dataclass
class OperationMetadata:
    """Metadata for an operation"""
    name: str
    description: str
    parameters: List[ParameterDefinition] = field(default_factory=list)
    returns: Optional[str] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


class OperationContext:
    """Context passed to operation handlers"""
    
    def __init__(
        self,
        tool_name: str,
        operation_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.tool_name = tool_name
        self.operation_name = operation_name
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.start_time = asyncio.get_event_loop().time()
        
    def get_execution_time(self) -> float:
        """Get execution time in seconds"""
        return asyncio.get_event_loop().time() - self.start_time


class BaseOperationHandler(ABC):
    """
    Base class for all operation handlers.
    
    Operation handlers implement the actual logic for specific operations
    within a tool. They can be dynamically loaded and support:
    - Parameter validation
    - Pre/post processing hooks
    - Error handling
    - Caching
    - Rate limiting
    """
    
    def __init__(self):
        self._middleware: List[Callable] = []
        self._cache: Optional[Dict[str, Any]] = None
        
    @property
    @abstractmethod
    def metadata(self) -> OperationMetadata:
        """Return operation metadata"""
        pass
    
    async def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters"""
        validated = {}
        errors = []
        
        for param_def in self.metadata.parameters:
            value = params.get(param_def.name, param_def.default)
            
            if not param_def.validate(value):
                errors.append(f"Invalid value for parameter '{param_def.name}'")
                continue
                
            if value is not None or param_def.required:
                validated[param_def.name] = value
                
        if errors:
            raise ValueError(f"Parameter validation failed: {', '.join(errors)}")
            
        return validated
    
    async def pre_execute(self, context: OperationContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """Hook called before execution"""
        return params
    
    @abstractmethod
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute the operation"""
        pass
    
    async def post_execute(self, context: OperationContext, result: Dict[str, Any]) -> Dict[str, Any]:
        """Hook called after execution"""
        return result
    
    async def handle_error(self, context: OperationContext, error: Exception) -> Dict[str, Any]:
        """Handle errors during execution"""
        return {
            "error": error.__class__.__name__,
            "message": str(error),
            "operation": context.operation_name,
            "tool": context.tool_name
        }
    
    async def __call__(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute the operation with full lifecycle"""
        try:
            # Validate parameters
            validated_params = await self.validate_parameters(params)
            
            # Pre-execute hook
            processed_params = await self.pre_execute(context, validated_params)
            
            # Execute operation
            result = await self.execute(context, **processed_params)
            
            # Post-execute hook
            final_result = await self.post_execute(context, result)
            
            return final_result
            
        except Exception as e:
            return await self.handle_error(context, e)


class BatchOperationHandler(BaseOperationHandler):
    """Base class for operations that support batch processing"""
    
    @abstractmethod
    async def execute_batch(self, context: OperationContext, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute operation on multiple items"""
        pass
    
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute single or batch operation"""
        if "items" in params and isinstance(params["items"], list):
            results = await self.execute_batch(context, params["items"])
            return {"results": results, "count": len(results)}
        else:
            # Single item execution
            return await self.execute_single(context, **params)
    
    @abstractmethod
    async def execute_single(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute operation on single item"""
        pass


class StreamingOperationHandler(BaseOperationHandler):
    """Base class for operations that support streaming responses"""
    
    @abstractmethod
    async def execute_stream(
        self, 
        context: OperationContext, 
        **params
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute operation with streaming response"""
        pass
    
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute with optional streaming"""
        if params.get("stream", False):
            # Return streaming response
            return {
                "stream": True,
                "generator": self.execute_stream(context, **params)
            }
        else:
            # Collect all results
            results = []
            async for item in self.execute_stream(context, **params):
                results.append(item)
            return {"results": results}


class CachedOperationHandler(BaseOperationHandler):
    """Base class for operations with built-in caching"""
    
    def __init__(self, cache_ttl: int = 300):
        super().__init__()
        self.cache_ttl = cache_ttl
        self._cache = {}
        
    def get_cache_key(self, context: OperationContext, params: Dict[str, Any]) -> str:
        """Generate cache key for parameters"""
        import hashlib
        import json
        
        cache_data = {
            "tool": context.tool_name,
            "operation": context.operation_name,
            "params": params
        }
        
        return hashlib.md5(
            json.dumps(cache_data, sort_keys=True).encode()
        ).hexdigest()
    
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute with caching"""
        cache_key = self.get_cache_key(context, params)
        
        # Check cache
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if asyncio.get_event_loop().time() - cached_time < self.cache_ttl:
                return {**cached_result, "_cached": True}
        
        # Execute and cache
        result = await super().execute(context, **params)
        self._cache[cache_key] = (asyncio.get_event_loop().time(), result)
        
        return result


class CompositeOperationHandler(BaseOperationHandler):
    """Handler that composes multiple sub-operations"""
    
    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, BaseOperationHandler] = {}
        
    def add_handler(self, name: str, handler: BaseOperationHandler) -> None:
        """Add a sub-handler"""
        self._handlers[name] = handler
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute by delegating to sub-handlers"""
        sub_operation = params.get("sub_operation")
        if not sub_operation or sub_operation not in self._handlers:
            raise ValueError(f"Unknown sub-operation: {sub_operation}")
            
        handler = self._handlers[sub_operation]
        return await handler(context, **params)