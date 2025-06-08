"""
mem0_export Tool

Export and import memory data with custom schemas.
Supports custom format handlers through plugins.
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_export"
TOOL_DESCRIPTION = """Memory export/import operations:
- Create export jobs with custom schemas
- Retrieve exported data
- Support for multiple export formats

Extensible with custom format handlers."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["create", "get"],
            "description": "The export operation to perform"
        },
        "schema": {"type": "object", "description": "Export schema definition"},
        "filters": {"type": "object", "description": "Filters for export"},
        "export_id": {"type": "string", "description": "Export job ID"},
        "user_id": {"type": "string", "description": "User ID filter"},
        "agent_id": {"type": "string", "description": "Agent ID filter"}
    },
    "required": ["operation"]
}


class CreateExportOperation(BaseOperationHandler):
    """Handler for creating export jobs"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="create",
            description="Create a memory export job",
            parameters=[
                ParameterDefinition("schema", ParameterType.OBJECT, "Export schema definition", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Filters for export", required=False),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute create export operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Build export configuration
            export_config = {
                "schema": params.get("schema", self._get_default_schema()),
                "filters": self._build_filters(params)
            }
            
            # Create export job
            result = await client.create_memory_export(**export_config)
            
            return {
                "status": "success",
                "data": result,
                "operation": "create",
                "export_id": result.get("export_id"),
                "message": "Export job created successfully"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _get_default_schema(self) -> Dict[str, Any]:
        """Get default export schema"""
        return {
            "format": "json",
            "include_metadata": True,
            "include_timestamps": True,
            "flatten_structure": False
        }
        
    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters from parameters"""
        filters = params.get("filters", {})
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                filters[key] = params[key]
        return filters


class GetExportOperation(BaseOperationHandler):
    """Handler for retrieving export data"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get",
            description="Retrieve export data",
            parameters=[
                ParameterDefinition("export_id", ParameterType.STRING, "Export job ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get export operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Get export data
            result = await client.get_memory_export(export_id=params["export_id"])
            
            # Check if export is ready
            if result.get("status") == "completed":
                return {
                    "status": "success",
                    "data": result,
                    "operation": "get",
                    "export_id": params["export_id"],
                    "export_data": result.get("data"),
                    "record_count": len(result.get("data", []))
                }
            else:
                return {
                    "status": "pending",
                    "data": result,
                    "operation": "get",
                    "export_id": params["export_id"],
                    "message": f"Export job is {result.get('status', 'in progress')}"
                }
                
        except Exception as e:
            return await self.handle_error(context, e)


# Additional export format handlers can be added as plugins
class CSVExportHandler(BaseOperationHandler):
    """Handler for CSV export format"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="export_csv",
            description="Export memories to CSV format",
            parameters=[
                ParameterDefinition("memories", ParameterType.ARRAY, "Memories to export", required=True),
                ParameterDefinition("columns", ParameterType.ARRAY, "Columns to include", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute CSV export"""
        import csv
        import io
        
        memories = params.get("memories", [])
        columns = params.get("columns", ["id", "memory", "user_id", "created_at"])
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for memory in memories:
            row = {col: memory.get(col, "") for col in columns}
            writer.writerow(row)
            
        csv_content = output.getvalue()
        output.close()
        
        return {
            "status": "success",
            "format": "csv",
            "content": csv_content,
            "row_count": len(memories)
        }


class MarkdownExportHandler(BaseOperationHandler):
    """Handler for Markdown export format"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="export_markdown",
            description="Export memories to Markdown format",
            parameters=[
                ParameterDefinition("memories", ParameterType.ARRAY, "Memories to export", required=True),
                ParameterDefinition("include_metadata", ParameterType.BOOLEAN, "Include metadata", required=False, default=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute Markdown export"""
        memories = params.get("memories", [])
        include_metadata = params.get("include_metadata", True)
        
        # Create Markdown content
        content = "# Memory Export\n\n"
        
        for memory in memories:
            content += f"## Memory {memory.get('id', 'Unknown')}\n\n"
            content += f"{memory.get('memory', '')}\n\n"
            
            if include_metadata:
                content += "**Metadata:**\n"
                content += f"- User: {memory.get('user_id', 'N/A')}\n"
                content += f"- Created: {memory.get('created_at', 'N/A')}\n"
                content += f"- Categories: {', '.join(memory.get('categories', []))}\n"
                content += "\n---\n\n"
                
        return {
            "status": "success",
            "format": "markdown",
            "content": content,
            "memory_count": len(memories)
        }


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in export operations"""
    return {
        "create": CreateExportOperation(),
        "get": GetExportOperation(),
        # Format handlers can be registered as sub-operations
        "export_csv": CSVExportHandler(),
        "export_markdown": MarkdownExportHandler()
    }