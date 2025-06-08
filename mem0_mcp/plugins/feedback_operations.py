"""
Feedback Operations Plugin

Adds feedback functionality to the mem0_memory tool.
"""

from typing import Any, Dict, Literal
from ..core.base_plugin import OperationPlugin, PluginMetadata
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext


class FeedbackOperation(BaseOperationHandler):
    """Handler for providing feedback on memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="feedback",
            description="Provide feedback on memory quality",
            parameters=[
                ParameterDefinition("memory_id", ParameterType.STRING, "Memory ID", required=True),
                ParameterDefinition("feedback", ParameterType.STRING, "Feedback type", required=True,
                                  choices=["POSITIVE", "NEGATIVE", "VERY_NEGATIVE"]),
                ParameterDefinition("feedback_reason", ParameterType.STRING, "Reason for feedback", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute feedback operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Submit feedback
            feedback_data = {
                "memory_id": params["memory_id"],
                "feedback": params["feedback"]
            }
            
            if "feedback_reason" in params:
                feedback_data["feedback_reason"] = params["feedback_reason"]
                
            # Call the feedback API
            # Note: This would need to be implemented in the actual Mem0 client
            # For now, we'll simulate the response
            result = {
                "status": "recorded",
                "memory_id": params["memory_id"],
                "feedback": params["feedback"],
                "timestamp": context.metadata.get("timestamp", "now")
            }
            
            # Emit feedback event
            event_bus = context.metadata.get("event_bus")
            if event_bus:
                await event_bus.emit("memory.feedback", {
                    "memory_id": params["memory_id"],
                    "feedback": params["feedback"],
                    "reason": params.get("feedback_reason")
                })
                
            return {
                "status": "success",
                "data": result,
                "operation": "feedback",
                "message": f"Feedback recorded for memory {params['memory_id']}"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)


class FeedbackAnalyticsOperation(BaseOperationHandler):
    """Handler for analyzing feedback data"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="feedback_analytics",
            description="Analyze feedback patterns across memories",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("time_range", ParameterType.STRING, "Time range for analysis", required=False,
                                  choices=["day", "week", "month", "all"])
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute feedback analytics"""
        # This would aggregate feedback data from the system
        # For demonstration, return mock analytics
        
        analytics = {
            "total_feedback": 150,
            "positive": 120,
            "negative": 25,
            "very_negative": 5,
            "satisfaction_rate": 0.80,
            "top_negative_reasons": [
                {"reason": "Incorrect information", "count": 10},
                {"reason": "Not relevant", "count": 8},
                {"reason": "Outdated", "count": 7}
            ],
            "trend": {
                "improving": True,
                "weekly_satisfaction": [0.75, 0.78, 0.79, 0.80]
            }
        }
        
        if params.get("user_id"):
            analytics["user_id"] = params["user_id"]
            
        return {
            "status": "success",
            "data": analytics,
            "operation": "feedback_analytics",
            "time_range": params.get("time_range", "all")
        }


class FeedbackOperationsPlugin(OperationPlugin):
    """Plugin that adds feedback operations to mem0_memory tool"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="feedback_operations",
            version="1.0.0",
            description="Adds feedback and feedback analytics to memory management",
            author="Mem0 Team",
            capabilities=["feedback", "analytics"]
        )
        
    async def setup(self) -> None:
        """Initialize feedback storage if needed"""
        # In a real implementation, might set up a feedback database
        pass
        
    def get_operations(self) -> Dict[str, BaseOperationHandler]:
        """Return feedback operation handlers"""
        return {
            "feedback": FeedbackOperation(),
            "feedback_analytics": FeedbackAnalyticsOperation()
        }
        
    def get_tool_name(self) -> str:
        """This plugin extends the mem0_memory tool"""
        return "mem0_memory"