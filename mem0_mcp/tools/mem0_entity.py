"""
mem0_entity Tool

Entity management operations for users, agents, apps, and runs.
Supports extensible entity types through plugins.
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_entity"
TOOL_DESCRIPTION = """Entity management operations including:
- List entities with filtering
- Get specific entity details
- Delete entities and their memories
- Reset all entities

Supports custom entity types through plugins."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["list", "get", "delete", "reset"],
            "description": "The entity operation to perform"
        },
        "entity_type": {
            "type": "string",
            "enum": ["user", "agent", "app", "run"],
            "description": "Type of entity"
        },
        "entity_id": {"type": "string", "description": "Entity ID"},
        "filters": {"type": "object", "description": "Filters for listing entities"}
    },
    "required": ["operation"]
}


class ListEntitiesOperation(BaseOperationHandler):
    """Handler for listing entities"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="list",
            description="List all entities with optional filters",
            parameters=[
                ParameterDefinition("entity_type", ParameterType.STRING, "Entity type to list", required=False,
                                  choices=["user", "agent", "app", "run"]),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute list entities operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            entity_type = params.get("entity_type")
            filters = params.get("filters", {})
            
            # Get entities based on type
            if entity_type == "user":
                result = await client.get_users(**filters)
            elif entity_type == "agent":
                # This would need to be implemented in the client
                result = {"entities": [], "type": "agent"}
            elif entity_type == "app":
                result = {"entities": [], "type": "app"}
            elif entity_type == "run":
                result = {"entities": [], "type": "run"}
            else:
                # List all entity types
                result = {
                    "users": await client.get_users(**filters),
                    "agents": [],
                    "apps": [],
                    "runs": []
                }
                
            return {
                "status": "success",
                "data": result,
                "operation": "list",
                "entity_type": entity_type
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class GetEntityOperation(BaseOperationHandler):
    """Handler for getting specific entity details"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get",
            description="Get details of a specific entity",
            parameters=[
                ParameterDefinition("entity_type", ParameterType.STRING, "Entity type", required=True,
                                  choices=["user", "agent", "app", "run"]),
                ParameterDefinition("entity_id", ParameterType.STRING, "Entity ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get entity operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            entity_type = params["entity_type"]
            entity_id = params["entity_id"]
            
            # Get entity details and associated memories
            entity_params = {f"{entity_type}_id": entity_id}
            memories = await client.get_all(**entity_params)
            
            result = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "memories": memories.get("results", []),
                "memory_count": len(memories.get("results", []))
            }
            
            return {
                "status": "success",
                "data": result,
                "operation": "get"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class DeleteEntityOperation(BaseOperationHandler):
    """Handler for deleting entities"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="delete",
            description="Delete an entity and all its memories",
            parameters=[
                ParameterDefinition("entity_type", ParameterType.STRING, "Entity type", required=True,
                                  choices=["user", "agent", "app", "run"]),
                ParameterDefinition("entity_id", ParameterType.STRING, "Entity ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute delete entity operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            entity_type = params["entity_type"]
            entity_id = params["entity_id"]
            
            # Delete all memories for this entity
            if entity_type == "user":
                result = await client.delete_users(user_id=entity_id)
            else:
                # For other entity types, use delete_all with filter
                entity_params = {f"{entity_type}_id": entity_id}
                result = await client.delete_all(**entity_params)
                
            return {
                "status": "success",
                "data": result,
                "operation": "delete",
                "entity_type": entity_type,
                "entity_id": entity_id
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class ResetEntitiesOperation(BaseOperationHandler):
    """Handler for resetting all entities"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="reset",
            description="Reset all entities and memories (CAUTION: This deletes all data)",
            parameters=[]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute reset operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # This would need to be implemented carefully
            # For now, return a warning
            return {
                "status": "warning",
                "message": "Reset operation not implemented for safety. Use delete operations for specific entities.",
                "operation": "reset"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in entity operations"""
    return {
        "list": ListEntitiesOperation(),
        "get": GetEntityOperation(),
        "delete": DeleteEntityOperation(),
        "reset": ResetEntitiesOperation()
    }