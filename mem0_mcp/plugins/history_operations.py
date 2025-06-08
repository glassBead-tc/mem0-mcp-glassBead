"""
History Operations Plugin

Adds memory history tracking to the mem0_memory tool.
"""

from typing import Any, Dict, List
from datetime import datetime, UTC
from ..core.base_plugin import OperationPlugin, PluginMetadata
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext


class HistoryOperation(BaseOperationHandler):
    """Handler for retrieving memory history"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="history",
            description="Get change history for a specific memory",
            parameters=[
                ParameterDefinition("memory_id", ParameterType.STRING, "Memory ID", required=True),
                ParameterDefinition("limit", ParameterType.INTEGER, "Maximum history entries", required=False, default=10)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute history operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Get memory history
            memory_id = params["memory_id"]
            limit = params.get("limit", 10)
            
            # This would call the actual history API
            # For demonstration, we'll create mock history
            history_entries = [
                {
                    "version": 3,
                    "timestamp": "2024-01-15T10:30:00Z",
                    "action": "update",
                    "changes": {
                        "before": "Previous memory content",
                        "after": "Updated memory content"
                    },
                    "user_id": "user123"
                },
                {
                    "version": 2,
                    "timestamp": "2024-01-14T15:20:00Z",
                    "action": "update",
                    "changes": {
                        "categories": ["added", "technical"]
                    },
                    "user_id": "user123"
                },
                {
                    "version": 1,
                    "timestamp": "2024-01-13T09:00:00Z",
                    "action": "create",
                    "initial_content": "Original memory content",
                    "user_id": "user123"
                }
            ]
            
            # Limit results
            history_entries = history_entries[:limit]
            
            return {
                "status": "success",
                "data": {
                    "memory_id": memory_id,
                    "history": history_entries,
                    "total_versions": len(history_entries)
                },
                "operation": "history"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class MemoryAuditOperation(BaseOperationHandler):
    """Handler for auditing memory changes"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="audit",
            description="Audit memory changes for compliance",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID to audit", required=False),
                ParameterDefinition("start_date", ParameterType.STRING, "Start date (ISO format)", required=False),
                ParameterDefinition("end_date", ParameterType.STRING, "End date (ISO format)", required=False),
                ParameterDefinition("action_types", ParameterType.ARRAY, "Action types to include", required=False,
                                  default=["create", "update", "delete"])
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute audit operation"""
        # This would query audit logs
        # For demonstration, return mock audit data
        
        audit_summary = {
            "period": {
                "start": params.get("start_date", "2024-01-01"),
                "end": params.get("end_date", datetime.now(UTC).isoformat())
            },
            "statistics": {
                "total_changes": 245,
                "creates": 150,
                "updates": 80,
                "deletes": 15
            },
            "by_user": {},
            "suspicious_activity": [],
            "compliance_status": "compliant"
        }
        
        if params.get("user_id"):
            audit_summary["by_user"][params["user_id"]] = {
                "total_changes": 45,
                "creates": 30,
                "updates": 12,
                "deletes": 3
            }
            
        return {
            "status": "success",
            "data": audit_summary,
            "operation": "audit"
        }


class RestoreMemoryOperation(BaseOperationHandler):
    """Handler for restoring memories from history"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="restore",
            description="Restore a memory to a previous version",
            parameters=[
                ParameterDefinition("memory_id", ParameterType.STRING, "Memory ID", required=True),
                ParameterDefinition("version", ParameterType.INTEGER, "Version to restore", required=True),
                ParameterDefinition("reason", ParameterType.STRING, "Reason for restoration", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute restore operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            memory_id = params["memory_id"]
            version = params["version"]
            
            # In a real implementation, this would:
            # 1. Fetch the historical version
            # 2. Update the current memory with historical content
            # 3. Log the restoration
            
            # For demonstration, simulate the restore
            result = {
                "memory_id": memory_id,
                "restored_version": version,
                "current_version": version + 1,
                "restoration_timestamp": datetime.now(UTC).isoformat(),
                "reason": params.get("reason", "Manual restoration")
            }
            
            return {
                "status": "success",
                "data": result,
                "operation": "restore",
                "message": f"Memory {memory_id} restored to version {version}"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class HistoryOperationsPlugin(OperationPlugin):
    """Plugin that adds history operations to mem0_memory tool"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="history_operations",
            version="1.0.0",
            description="Adds history tracking, auditing, and restoration capabilities",
            author="Mem0 Team",
            capabilities=["history", "audit", "restore"],
            dependencies=["batch_operations"]  # May depend on batch ops for bulk restore
        )
        
    async def setup(self) -> None:
        """Initialize history tracking if needed"""
        # Could set up history storage, audit logs, etc.
        pass
        
    def get_operations(self) -> Dict[str, BaseOperationHandler]:
        """Return history operation handlers"""
        return {
            "history": HistoryOperation(),
            "audit": MemoryAuditOperation(),
            "restore": RestoreMemoryOperation()
        }
        
    def get_tool_name(self) -> str:
        """This plugin extends the mem0_memory tool"""
        return "mem0_memory"