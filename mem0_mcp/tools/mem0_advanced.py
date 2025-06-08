"""
mem0_advanced Tool

Advanced features including multimodal content and analytics.
Extensible with custom analyzers and processors.
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_advanced"
TOOL_DESCRIPTION = """Advanced memory operations:
- Add multimodal memories (images, documents)
- Analyze memory patterns and statistics
- System health checks
- Custom processors and analyzers

Extensible with advanced feature plugins."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["add_multimodal", "analyze", "health"],
            "description": "The advanced operation to perform"
        },
        "messages": {"type": "array", "description": "Messages with multimodal content"},
        "user_id": {"type": "string", "description": "User ID"},
        "agent_id": {"type": "string", "description": "Agent ID"},
        "analysis_type": {
            "type": "string",
            "enum": ["patterns", "statistics", "usage"],
            "description": "Type of analysis"
        },
        "filters": {"type": "object", "description": "Filters for analysis"}
    },
    "required": ["operation"]
}


class AddMultimodalOperation(BaseOperationHandler):
    """Handler for adding multimodal memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="add_multimodal",
            description="Add memories with multimodal content (images, documents)",
            parameters=[
                ParameterDefinition("messages", ParameterType.ARRAY, "Messages with multimodal content", required=True),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute add multimodal operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            # Process multimodal content
            processed_messages = []
            content_types = []
            
            for message in params.get("messages", []):
                processed_message = {"role": message.get("role", "user")}
                
                # Handle different content types
                if isinstance(message.get("content"), list):
                    processed_content = []
                    for content_item in message["content"]:
                        if content_item.get("type") == "text":
                            processed_content.append(content_item)
                            content_types.append("text")
                            
                        elif content_item.get("type") == "image_url":
                            # Process image
                            processed_item = await self._process_image(content_item)
                            processed_content.append(processed_item)
                            content_types.append("image")
                            
                        elif content_item.get("type") == "document_url":
                            # Process document
                            processed_item = await self._process_document(content_item)
                            processed_content.append(processed_item)
                            content_types.append("document")
                            
                    processed_message["content"] = processed_content
                else:
                    processed_message["content"] = message.get("content", "")
                    content_types.append("text")
                    
                processed_messages.append(processed_message)
                
            # Add to memory
            entity_params = self._extract_entity_params(params)
            result = await client.add(
                messages=processed_messages,
                **entity_params,
                metadata={"content_types": list(set(content_types))}
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "add_multimodal",
                "content_types": list(set(content_types)),
                "message_count": len(processed_messages)
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    async def _process_image(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process image content"""
        # In a real implementation, this might:
        # - Download and store the image
        # - Extract text using OCR
        # - Generate image description using vision models
        return {
            "type": "text",
            "text": f"[Image: {content_item.get('image_url', {}).get('url', 'Unknown')}]"
        }
        
    async def _process_document(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process document content"""
        # In a real implementation, this might:
        # - Download and parse the document
        # - Extract text content
        # - Process structured data
        return {
            "type": "text",
            "text": f"[Document: {content_item.get('document_url', 'Unknown')}]"
        }
        
    def _extract_entity_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity parameters from params"""
        entity_params = {}
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                entity_params[key] = params[key]
        return entity_params


class AnalyzeMemoriesOperation(BaseOperationHandler):
    """Handler for analyzing memory patterns"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="analyze",
            description="Analyze memory patterns and statistics",
            parameters=[
                ParameterDefinition("analysis_type", ParameterType.STRING, "Type of analysis", required=True,
                                  choices=["patterns", "statistics", "usage"]),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute analyze operation"""
        from mem0 import AsyncMemoryClient
        client = context.metadata.get("client")
        
        if not client:
            return {"error": "Memory client not initialized"}
            
        try:
            analysis_type = params["analysis_type"]
            entity_params = self._extract_entity_params(params)
            
            # Get memories for analysis
            memories = await client.get_all(**entity_params, page_size=1000)
            memory_list = memories.get("results", [])
            
            if analysis_type == "patterns":
                result = await self._analyze_patterns(memory_list)
            elif analysis_type == "statistics":
                result = await self._analyze_statistics(memory_list)
            elif analysis_type == "usage":
                result = await self._analyze_usage(memory_list, entity_params)
            else:
                result = {"error": f"Unknown analysis type: {analysis_type}"}
                
            return {
                "status": "success",
                "data": result,
                "operation": "analyze",
                "analysis_type": analysis_type,
                "memory_count": len(memory_list)
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    async def _analyze_patterns(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze memory patterns"""
        from collections import Counter, defaultdict
        import re
        
        # Extract patterns
        categories = Counter()
        topics = defaultdict(int)
        word_freq = Counter()
        
        for memory in memories:
            # Categories
            for cat in memory.get("categories", []):
                categories[cat] += 1
                
            # Extract topics/keywords
            text = memory.get("memory", "")
            words = re.findall(r'\b\w+\b', text.lower())
            word_freq.update(words)
            
        # Get top patterns
        return {
            "top_categories": dict(categories.most_common(10)),
            "top_words": dict(word_freq.most_common(20)),
            "category_count": len(categories),
            "unique_words": len(word_freq)
        }
        
    async def _analyze_statistics(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate memory statistics"""
        from datetime import datetime
        
        total_memories = len(memories)
        
        # Time-based statistics
        if memories:
            dates = []
            for memory in memories:
                if "created_at" in memory:
                    try:
                        dates.append(datetime.fromisoformat(memory["created_at"].replace("Z", "+00:00")))
                    except:
                        pass
                        
            if dates:
                earliest = min(dates)
                latest = max(dates)
                duration = (latest - earliest).days
            else:
                earliest = latest = duration = None
        else:
            earliest = latest = duration = None
            
        # Memory length statistics
        lengths = [len(memory.get("memory", "")) for memory in memories]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        
        return {
            "total_memories": total_memories,
            "earliest_memory": earliest.isoformat() if earliest else None,
            "latest_memory": latest.isoformat() if latest else None,
            "duration_days": duration,
            "average_memory_length": avg_length,
            "min_memory_length": min(lengths) if lengths else 0,
            "max_memory_length": max(lengths) if lengths else 0
        }
        
    async def _analyze_usage(self, memories: List[Dict[str, Any]], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze memory usage patterns"""
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        # Group by time periods
        daily_counts = defaultdict(int)
        hourly_counts = defaultdict(int)
        
        for memory in memories:
            if "created_at" in memory:
                try:
                    dt = datetime.fromisoformat(memory["created_at"].replace("Z", "+00:00"))
                    daily_counts[dt.date()] += 1
                    hourly_counts[dt.hour] += 1
                except:
                    pass
                    
        # Calculate trends
        if daily_counts:
            dates = sorted(daily_counts.keys())
            recent_days = 7
            recent_counts = [daily_counts[d] for d in dates[-recent_days:]]
            avg_daily = sum(recent_counts) / len(recent_counts) if recent_counts else 0
        else:
            avg_daily = 0
            
        return {
            "daily_average": avg_daily,
            "peak_hour": max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else None,
            "total_days_active": len(daily_counts),
            "filters_used": filters
        }
        
    def _extract_entity_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity parameters from params"""
        entity_params = {}
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                entity_params[key] = params[key]
        return entity_params


class HealthCheckOperation(BaseOperationHandler):
    """Handler for system health checks"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="health",
            description="Perform system health check",
            parameters=[]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute health check"""
        from mem0 import AsyncMemoryClient
        import time
        
        client = context.metadata.get("client")
        
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": time.time()
        }
        
        # Check API connectivity
        if client:
            start_time = time.time()
            try:
                await client.get_project()
                health_status["checks"]["api"] = {
                    "status": "healthy",
                    "response_time_ms": int((time.time() - start_time) * 1000)
                }
            except Exception as e:
                health_status["checks"]["api"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "unhealthy"
        else:
            health_status["checks"]["api"] = {
                "status": "unhealthy",
                "error": "Client not initialized"
            }
            health_status["status"] = "unhealthy"
            
        # Check graph memory if enabled
        graph_client = context.metadata.get("graph_client")
        if graph_client:
            try:
                # Simple connectivity check
                graph_client.get_all(filters={}, limit=1)
                health_status["checks"]["graph"] = {"status": "healthy"}
            except Exception as e:
                health_status["checks"]["graph"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                
        # Check configuration
        config_manager = context.metadata.get("config_manager")
        if config_manager:
            health_status["checks"]["config"] = {
                "status": "healthy" if config_manager._loaded else "unhealthy",
                "loaded": config_manager._loaded
            }
            
        # Check plugins
        plugin_registry = context.metadata.get("plugin_registry")
        if plugin_registry:
            plugin_count = len(plugin_registry.get_plugin_info())
            health_status["checks"]["plugins"] = {
                "status": "healthy",
                "count": plugin_count
            }
            
        return {
            "status": "success",
            "data": health_status,
            "operation": "health"
        }


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in advanced operations"""
    return {
        "add_multimodal": AddMultimodalOperation(),
        "analyze": AnalyzeMemoriesOperation(),
        "health": HealthCheckOperation()
    }