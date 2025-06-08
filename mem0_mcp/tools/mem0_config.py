"""
mem0_config Tool

Project and organization configuration management.
Supports dynamic configuration updates and custom configuration providers.
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_config"
TOOL_DESCRIPTION = """Configuration and project management:
- Get project configuration
- Update project settings
- Check configuration status
- Manage custom instructions and categories

Extensible with custom configuration providers."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["get_project", "update_project", "status"],
            "description": "The configuration operation to perform"
        },
        "fields": {"type": "array", "description": "Fields to retrieve"},
        "custom_instructions": {"type": "string", "description": "Custom extraction instructions"},
        "custom_categories": {"type": "array", "description": "Custom memory categories"},
        "retrieval_criteria": {"type": "array", "description": "Custom retrieval criteria"},
        "enable_graph": {"type": "boolean", "description": "Enable graph memory"},
        "version": {"type": "string", "description": "API version"}
    },
    "required": ["operation"]
}


class GetProjectOperation(BaseOperationHandler):
    """Handler for getting project configuration"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get_project",
            description="Get current project configuration",
            parameters=[
                ParameterDefinition("fields", ParameterType.ARRAY, "Specific fields to retrieve", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get project configuration"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        config_manager = context.metadata.get("config_manager")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Get project info from API
            project_info = await client.get_project()
            
            # Merge with local configuration
            if config_manager:
                local_config = {
                    "defaults": config_manager.get("defaults", {}),
                    "features": config_manager.get("features", {}),
                    "performance": config_manager.get("performance", {})
                }
                project_info["local_config"] = local_config
                
            # Filter fields if requested
            fields = params.get("fields")
            if fields:
                filtered_info = {}
                for field in fields:
                    if field in project_info:
                        filtered_info[field] = project_info[field]
                project_info = filtered_info
                
            return {
                "status": "success",
                "data": project_info,
                "operation": "get_project"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class UpdateProjectOperation(BaseOperationHandler):
    """Handler for updating project configuration"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="update_project",
            description="Update project configuration",
            parameters=[
                ParameterDefinition("custom_instructions", ParameterType.STRING, "Custom extraction instructions", required=False),
                ParameterDefinition("custom_categories", ParameterType.ARRAY, "Custom memory categories", required=False),
                ParameterDefinition("retrieval_criteria", ParameterType.ARRAY, "Custom retrieval criteria", required=False),
                ParameterDefinition("enable_graph", ParameterType.BOOLEAN, "Enable graph memory", required=False),
                ParameterDefinition("version", ParameterType.STRING, "API version", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute update project configuration"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        config_manager = context.metadata.get("config_manager")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Build update payload
            update_data = {}
            
            if "custom_instructions" in params:
                update_data["custom_instructions"] = params["custom_instructions"]
                
            if "custom_categories" in params:
                update_data["custom_categories"] = params["custom_categories"]
                
            if "retrieval_criteria" in params:
                update_data["retrieval_criteria"] = params["retrieval_criteria"]
                
            # Update project via API
            result = await client.update_project(**update_data)
            
            # Update local configuration if applicable
            if config_manager:
                if "enable_graph" in params:
                    config_manager.set("features.graph_memory", params["enable_graph"])
                    
                if "version" in params:
                    config_manager.set("api.version", params["version"])
                    
                # Save configuration
                await config_manager.save()
                
            return {
                "status": "success",
                "data": result,
                "operation": "update_project",
                "updated_fields": list(update_data.keys())
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class ConfigStatusOperation(BaseOperationHandler):
    """Handler for checking configuration status"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="status",
            description="Get configuration status and health check",
            parameters=[]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute configuration status check"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        config_manager = context.metadata.get("config_manager")
        plugin_registry = context.metadata.get("plugin_registry")
        
        status = {
            "api_connected": False,
            "config_loaded": False,
            "plugins_loaded": False,
            "features": {},
            "warnings": [],
            "info": {}
        }
        
        try:
            # Check API connection
            if client:
                try:
                    project = await client.get_project()
                    status["api_connected"] = True
                    status["info"]["project_id"] = project.get("id")
                    status["info"]["organization"] = project.get("organization")
                except:
                    status["warnings"].append("Unable to connect to Mem0 API")
                    
            # Check configuration
            if config_manager:
                status["config_loaded"] = config_manager._loaded
                status["features"] = config_manager.get("features", {})
                
                # Check for required config
                if not config_manager.get("api.key"):
                    status["warnings"].append("API key not configured")
                    
            # Check plugins
            if plugin_registry:
                plugin_info = plugin_registry.get_plugin_info()
                status["plugins_loaded"] = len(plugin_info) > 0
                status["info"]["plugin_count"] = len(plugin_info)
                status["info"]["plugins"] = [p["name"] for p in plugin_info]
                
            # Overall health
            status["healthy"] = (
                status["api_connected"] and 
                status["config_loaded"] and 
                len(status["warnings"]) == 0
            )
            
            return {
                "status": "success",
                "data": status,
                "operation": "status"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


# Additional configuration operations can be added
class ConfigValidationOperation(BaseOperationHandler):
    """Handler for validating configuration"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="validate",
            description="Validate configuration against schema",
            parameters=[
                ParameterDefinition("config", ParameterType.OBJECT, "Configuration to validate", required=True),
                ParameterDefinition("schema", ParameterType.OBJECT, "Validation schema", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute configuration validation"""
        config = params.get("config", {})
        schema = params.get("schema")
        
        errors = []
        warnings = []
        
        # Basic validation
        if not config.get("api", {}).get("key"):
            errors.append("API key is required")
            
        # Feature compatibility checks
        if config.get("features", {}).get("graph_memory") and not config.get("graph_store"):
            warnings.append("Graph memory enabled but no graph store configured")
            
        # Version compatibility
        api_version = config.get("api", {}).get("version", "v2")
        if api_version not in ["v1", "v1.1", "v2"]:
            warnings.append(f"Unknown API version: {api_version}")
            
        return {
            "status": "success" if not errors else "error",
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "operation": "validate"
        }


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in configuration operations"""
    return {
        "get_project": GetProjectOperation(),
        "update_project": UpdateProjectOperation(),
        "status": ConfigStatusOperation(),
        "validate": ConfigValidationOperation()
    }