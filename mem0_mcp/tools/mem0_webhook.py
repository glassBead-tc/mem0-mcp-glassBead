"""
mem0_webhook Tool

Webhook management for event notifications.
Supports custom event handlers through plugins.
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_webhook"
TOOL_DESCRIPTION = """Webhook management operations:
- Create webhooks for event notifications
- Get webhook configuration
- Update webhook settings
- Delete webhooks

Extensible with custom event handlers."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["create", "get", "update", "delete"],
            "description": "The webhook operation to perform"
        },
        "webhook_id": {"type": "integer", "description": "Webhook ID"},
        "url": {"type": "string", "description": "Webhook URL"},
        "name": {"type": "string", "description": "Webhook name"},
        "project_id": {"type": "string", "description": "Project ID"},
        "event_types": {"type": "array", "description": "Event types to subscribe to"}
    },
    "required": ["operation"]
}


class CreateWebhookOperation(BaseOperationHandler):
    """Handler for creating webhooks"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="create",
            description="Create a new webhook",
            parameters=[
                ParameterDefinition("url", ParameterType.STRING, "Webhook URL", required=True),
                ParameterDefinition("name", ParameterType.STRING, "Webhook name", required=True),
                ParameterDefinition("project_id", ParameterType.STRING, "Project ID", required=False),
                ParameterDefinition("event_types", ParameterType.ARRAY, "Event types to subscribe to", required=False,
                                  default=["memory.added", "memory.updated", "memory.deleted"])
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute create webhook operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Create webhook
            webhook_data = {
                "url": params["url"],
                "name": params["name"],
                "event_types": params.get("event_types", ["memory.added", "memory.updated", "memory.deleted"])
            }
            
            if "project_id" in params:
                webhook_data["project_id"] = params["project_id"]
                
            result = await client.create_webhook(**webhook_data)
            
            # Register webhook in local event system if available
            event_bus = context.metadata.get("event_bus")
            if event_bus:
                await self._register_webhook_handler(event_bus, result)
                
            return {
                "status": "success",
                "data": result,
                "operation": "create",
                "webhook_id": result.get("id"),
                "message": "Webhook created successfully"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    async def _register_webhook_handler(self, event_bus, webhook_config):
        """Register webhook handler in event bus"""
        import httpx
        
        async def webhook_handler(event):
            """Send event to webhook"""
            if event.name in webhook_config.get("event_types", []):
                async with httpx.AsyncClient() as client:
                    try:
                        await client.post(
                            webhook_config["url"],
                            json={
                                "event": event.name,
                                "data": event.data,
                                "timestamp": event.timestamp.isoformat(),
                                "webhook_id": webhook_config["id"]
                            },
                            timeout=30
                        )
                    except Exception as e:
                        # Log error but don't fail
                        pass
                        
        # Register handler for each event type
        for event_type in webhook_config.get("event_types", []):
            event_bus.subscribe(event_type, webhook_handler)


class GetWebhookOperation(BaseOperationHandler):
    """Handler for getting webhook configuration"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get",
            description="Get webhook configuration",
            parameters=[
                ParameterDefinition("webhook_id", ParameterType.INTEGER, "Webhook ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get webhook operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Get webhook details
            result = await client.get_webhook(webhook_id=params["webhook_id"])
            
            return {
                "status": "success",
                "data": result,
                "operation": "get",
                "webhook_id": params["webhook_id"]
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class UpdateWebhookOperation(BaseOperationHandler):
    """Handler for updating webhooks"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="update",
            description="Update webhook settings",
            parameters=[
                ParameterDefinition("webhook_id", ParameterType.INTEGER, "Webhook ID", required=True),
                ParameterDefinition("url", ParameterType.STRING, "New webhook URL", required=False),
                ParameterDefinition("name", ParameterType.STRING, "New webhook name", required=False),
                ParameterDefinition("event_types", ParameterType.ARRAY, "New event types", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute update webhook operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Build update data
            update_data = {}
            for field in ["url", "name", "event_types"]:
                if field in params:
                    update_data[field] = params[field]
                    
            if not update_data:
                return {
                    "status": "error",
                    "message": "No fields to update",
                    "operation": "update"
                }
                
            # Update webhook
            result = await client.update_webhook(
                webhook_id=params["webhook_id"],
                **update_data
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "update",
                "webhook_id": params["webhook_id"],
                "updated_fields": list(update_data.keys())
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class DeleteWebhookOperation(BaseOperationHandler):
    """Handler for deleting webhooks"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="delete",
            description="Delete a webhook",
            parameters=[
                ParameterDefinition("webhook_id", ParameterType.INTEGER, "Webhook ID", required=True)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute delete webhook operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Delete webhook
            result = await client.delete_webhook(webhook_id=params["webhook_id"])
            
            return {
                "status": "success",
                "data": result,
                "operation": "delete",
                "webhook_id": params["webhook_id"],
                "message": "Webhook deleted successfully"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


# Additional webhook-related operations
class TestWebhookOperation(BaseOperationHandler):
    """Handler for testing webhook connectivity"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="test",
            description="Test webhook connectivity",
            parameters=[
                ParameterDefinition("webhook_id", ParameterType.INTEGER, "Webhook ID", required=False),
                ParameterDefinition("url", ParameterType.STRING, "Webhook URL to test", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute webhook test"""
        import httpx
        from datetime import datetime, UTC
        
        # Get webhook URL
        if "webhook_id" in params:
            # Fetch webhook details
            client = context.metadata.get("client")
            if not client:
                return {"error": "Memory client not initialized"}
                
            webhook = await client.get_webhook(webhook_id=params["webhook_id"])
            url = webhook.get("url")
        elif "url" in params:
            url = params["url"]
        else:
            return {
                "status": "error",
                "message": "Either webhook_id or url is required",
                "operation": "test"
            }
            
        # Send test event
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "event": "webhook.test",
                        "data": {
                            "message": "This is a test webhook event",
                            "timestamp": datetime.now(UTC).isoformat()
                        }
                    },
                    timeout=30
                )
                
                return {
                    "status": "success",
                    "operation": "test",
                    "url": url,
                    "response_status": response.status_code,
                    "response_body": response.text if response.status_code < 400 else None,
                    "success": 200 <= response.status_code < 300
                }
                
        except httpx.TimeoutException:
            return {
                "status": "error",
                "operation": "test",
                "url": url,
                "error": "Webhook timeout (30s)"
            }
        except Exception as e:
            return {
                "status": "error",
                "operation": "test",
                "url": url,
                "error": str(e)
            }


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in webhook operations"""
    return {
        "create": CreateWebhookOperation(),
        "get": GetWebhookOperation(),
        "update": UpdateWebhookOperation(),
        "delete": DeleteWebhookOperation(),
        "test": TestWebhookOperation()
    }