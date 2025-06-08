"""
mem0_memory Tool

Core memory management operations including CRUD, search, and batch operations.
This tool provides an extensible architecture for memory operations.
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_memory"
TOOL_DESCRIPTION = """Comprehensive memory management operations including:
- Add, get, update, delete memories
- Search with semantic understanding
- Batch operations for efficiency
- Memory history tracking
- Feedback mechanisms

This tool supports extensibility through operation plugins."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["add", "get", "get_all", "search", "update", "delete", 
                    "delete_all", "history", "batch_update", "batch_delete", "feedback"],
            "description": "The memory operation to perform"
        },
        "memory_id": {"type": "string", "description": "Memory ID for specific operations"},
        "messages": {"type": "array", "description": "Messages to add as memories"},
        "query": {"type": "string", "description": "Search query"},
        "user_id": {"type": "string", "description": "User ID filter"},
        "agent_id": {"type": "string", "description": "Agent ID filter"},
        "app_id": {"type": "string", "description": "App ID filter"},
        "run_id": {"type": "string", "description": "Run ID filter"},
        "metadata": {"type": "object", "description": "Memory metadata"},
        "categories": {"type": "array", "description": "Memory categories"},
        "filters": {"type": "object", "description": "Additional filters"},
        "includes": {"type": "string", "description": "Fields to include"},
        "excludes": {"type": "string", "description": "Fields to exclude"},
        "infer": {"type": "boolean", "description": "Enable inference", "default": True},
        "page": {"type": "integer", "description": "Page number", "default": 1},
        "page_size": {"type": "integer", "description": "Page size", "default": 100},
        "version": {"type": "string", "description": "API version", "default": "v2"},
        "output_format": {"type": "string", "description": "Output format", "default": "v1.1"},
        "data": {"type": "string", "description": "Data for update operations"},
        "memories": {"type": "array", "description": "Memories for batch operations"},
        "feedback": {"type": "string", "enum": ["POSITIVE", "NEGATIVE", "VERY_NEGATIVE"]},
        "feedback_reason": {"type": "string", "description": "Reason for feedback"}
    },
    "required": ["operation"]
}


class AddMemoryOperation(BaseOperationHandler):
    """Handler for adding memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="add",
            description="Add new memories to the system",
            parameters=[
                ParameterDefinition("messages", ParameterType.ARRAY, "Messages to add", required=True),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID", required=False),
                ParameterDefinition("app_id", ParameterType.STRING, "App ID", required=False),
                ParameterDefinition("run_id", ParameterType.STRING, "Run ID", required=False),
                ParameterDefinition("metadata", ParameterType.OBJECT, "Additional metadata", required=False),
                ParameterDefinition("categories", ParameterType.ARRAY, "Memory categories", required=False),
                ParameterDefinition("infer", ParameterType.BOOLEAN, "Enable inference", required=False, default=True),
                ParameterDefinition("output_format", ParameterType.STRING, "Output format", required=False, default="v1.1")
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute add memory operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Extract entity parameters
            entity_params = self._extract_entity_params(params)
            
            # Add memories
            result = await client.add(
                messages=params["messages"],
                **entity_params,
                metadata=params.get("metadata"),
                categories=params.get("categories"),
                infer=params.get("infer", True),
                output_format=params.get("output_format", "v1.1")
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "add",
                "count": len(result.get("results", []))
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _extract_entity_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity parameters from params"""
        entity_params = {}
        for key in ["user_id", "agent_id", "app_id", "run_id"]:
            if key in params and params[key]:
                entity_params[key] = params[key]
        return entity_params


class SearchMemoryOperation(BaseOperationHandler):
    """Handler for searching memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="search",
            description="Search memories using semantic search",
            parameters=[
                ParameterDefinition("query", ParameterType.STRING, "Search query", required=True),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("app_id", ParameterType.STRING, "App ID filter", required=False),
                ParameterDefinition("run_id", ParameterType.STRING, "Run ID filter", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False),
                ParameterDefinition("version", ParameterType.STRING, "API version", required=False, default="v2"),
                ParameterDefinition("page", ParameterType.INTEGER, "Page number", required=False, default=1),
                ParameterDefinition("page_size", ParameterType.INTEGER, "Page size", required=False, default=100)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute search operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Extract entity parameters
            entity_params = self._extract_entity_params(params)
            
            # Perform search
            result = await client.search(
                query=params["query"],
                **entity_params,
                filters=params.get("filters"),
                version=params.get("version", "v2"),
                page=params.get("page", 1),
                page_size=params.get("page_size", 100)
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "search",
                "query": params["query"],
                "count": len(result.get("results", []))
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _extract_entity_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity parameters from params"""
        entity_params = {}
        for key in ["user_id", "agent_id", "app_id", "run_id"]:
            if key in params and params[key]:
                entity_params[key] = params[key]
        return entity_params


class GetMemoryOperation(BaseOperationHandler):
    """Handler for getting specific memory"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get",
            description="Get a specific memory by ID",
            parameters=[
                ParameterDefinition("memory_id", ParameterType.STRING, "Memory ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get memory operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            result = await client.get(memory_id=params["memory_id"])
            
            return {
                "status": "success",
                "data": result,
                "operation": "get",
                "memory_id": params["memory_id"]
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class UpdateMemoryOperation(BaseOperationHandler):
    """Handler for updating memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="update",
            description="Update an existing memory",
            parameters=[
                ParameterDefinition("memory_id", ParameterType.STRING, "Memory ID", required=True),
                ParameterDefinition("data", ParameterType.STRING, "Updated memory data", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute update operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            result = await client.update(
                memory_id=params["memory_id"],
                data=params["data"]
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "update",
                "memory_id": params["memory_id"]
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class DeleteMemoryOperation(BaseOperationHandler):
    """Handler for deleting memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="delete",
            description="Delete a specific memory",
            parameters=[
                ParameterDefinition("memory_id", ParameterType.STRING, "Memory ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute delete operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            result = await client.delete(memory_id=params["memory_id"])
            
            return {
                "status": "success",
                "data": result,
                "operation": "delete",
                "memory_id": params["memory_id"]
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class GetAllMemoriesOperation(BaseOperationHandler):
    """Handler for getting all memories with filters"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get_all",
            description="Get all memories with optional filters",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("app_id", ParameterType.STRING, "App ID filter", required=False),
                ParameterDefinition("run_id", ParameterType.STRING, "Run ID filter", required=False),
                ParameterDefinition("page", ParameterType.INTEGER, "Page number", required=False, default=1),
                ParameterDefinition("page_size", ParameterType.INTEGER, "Page size", required=False, default=100)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get all operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Extract entity parameters
            entity_params = self._extract_entity_params(params)
            
            result = await client.get_all(
                **entity_params,
                page=params.get("page", 1),
                page_size=params.get("page_size", 100)
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "get_all",
                "count": len(result.get("results", []))
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _extract_entity_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity parameters from params"""
        entity_params = {}
        for key in ["user_id", "agent_id", "app_id", "run_id"]:
            if key in params and params[key]:
                entity_params[key] = params[key]
        return entity_params


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in memory operations"""
    return {
        "add": AddMemoryOperation(),
        "search": SearchMemoryOperation(),
        "get": GetMemoryOperation(),
        "update": UpdateMemoryOperation(),
        "delete": DeleteMemoryOperation(),
        "get_all": GetAllMemoriesOperation(),
        # Additional operations can be added here or via plugins
    }