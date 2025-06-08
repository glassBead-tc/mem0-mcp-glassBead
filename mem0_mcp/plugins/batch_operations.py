"""
Batch Operations Plugin

Adds batch operation support to the mem0_memory tool.
"""

from typing import Any, Dict, List
from ..core.base_plugin import OperationPlugin, PluginMetadata
from ..core.base_operation import BatchOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext


class BatchUpdateOperation(BatchOperationHandler):
    """Handler for batch memory updates"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="batch_update",
            description="Update multiple memories in a single operation",
            parameters=[
                ParameterDefinition("memories", ParameterType.ARRAY, "Array of memory update objects", required=True)
            ]
        )
        
    async def execute_batch(self, context: OperationContext, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute batch update"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return [{"error": "Memory client not initialized"} for _ in items]
            
        results = []
        for item in items:
            try:
                result = await client.update(
                    memory_id=item["memory_id"],
                    data=item["data"]
                )
                results.append({
                    "status": "success",
                    "memory_id": item["memory_id"],
                    "data": result
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "memory_id": item.get("memory_id"),
                    "error": str(e)
                })
                
        return results
        
    async def execute_single(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Not used for batch operations"""
        return {"error": "Use 'memories' parameter for batch operations"}


class BatchDeleteOperation(BatchOperationHandler):
    """Handler for batch memory deletion"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="batch_delete",
            description="Delete multiple memories in a single operation",
            parameters=[
                ParameterDefinition("memory_ids", ParameterType.ARRAY, "Array of memory IDs to delete", required=True)
            ]
        )
        
    async def execute_batch(self, context: OperationContext, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute batch delete"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return [{"error": "Memory client not initialized"} for _ in items]
            
        # If items is a list of IDs, convert to proper format
        if items and isinstance(items[0], str):
            items = [{"memory_id": id} for id in items]
            
        results = []
        for item in items:
            try:
                memory_id = item.get("memory_id") if isinstance(item, dict) else item
                result = await client.delete(memory_id=memory_id)
                results.append({
                    "status": "success",
                    "memory_id": memory_id,
                    "data": result
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "memory_id": item.get("memory_id") if isinstance(item, dict) else item,
                    "error": str(e)
                })
                
        return results
        
    async def execute_single(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Not used for batch operations"""
        return {"error": "Use 'memory_ids' parameter for batch operations"}


class DeleteAllOperation(BatchOperationHandler):
    """Handler for deleting all memories with filters"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="delete_all",
            description="Delete all memories matching filters",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("app_id", ParameterType.STRING, "App ID filter", required=False),
                ParameterDefinition("run_id", ParameterType.STRING, "Run ID filter", required=False),
                ParameterDefinition("confirm", ParameterType.BOOLEAN, "Confirmation flag", required=True)
            ]
        )
        
    async def execute_single(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute delete all operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        if not params.get("confirm"):
            return {
                "status": "error",
                "message": "Delete all operation requires confirmation (confirm=true)"
            }
            
        try:
            # Extract entity parameters
            entity_params = {}
            for key in ["user_id", "agent_id", "app_id", "run_id"]:
                if key in params and params[key]:
                    entity_params[key] = params[key]
                    
            if not entity_params:
                return {
                    "status": "error",
                    "message": "At least one filter (user_id, agent_id, app_id, run_id) is required"
                }
                
            # Delete all matching memories
            result = await client.delete_all(**entity_params)
            
            return {
                "status": "success",
                "data": result,
                "operation": "delete_all",
                "filters": entity_params
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    async def execute_batch(self, context: OperationContext, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Not used for delete_all"""
        return []


class BatchOperationsPlugin(OperationPlugin):
    """Plugin that adds batch operations to mem0_memory tool"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="batch_operations",
            version="1.0.0",
            description="Adds batch update and delete operations to memory management",
            author="Mem0 Team",
            capabilities=["batch_operations"]
        )
        
    async def setup(self) -> None:
        """No setup required"""
        pass
        
    def get_operations(self) -> Dict[str, 'BaseOperationHandler']:
        """Return batch operation handlers"""
        return {
            "batch_update": BatchUpdateOperation(),
            "batch_delete": BatchDeleteOperation(),
            "delete_all": DeleteAllOperation()
        }
        
    def get_tool_name(self) -> str:
        """This plugin extends the mem0_memory tool"""
        return "mem0_memory"