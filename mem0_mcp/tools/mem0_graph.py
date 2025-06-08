"""
mem0_graph Tool

Graph memory operations for relationship-based data.
Supports pluggable graph backends (Neo4j, NetworkX, etc.).
"""

from typing import Any, Dict, List, Optional, Literal
from ..core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

TOOL_NAME = "mem0_graph"
TOOL_DESCRIPTION = """Graph memory operations for managing relationships:
- Add nodes and relationships to graph
- Search graph using semantic queries
- Retrieve all graph data
- Clear graph memory
- Visualize graph structure

Supports multiple graph backends through plugins."""

TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["add", "search", "get_all", "delete_all", "visualize"],
            "description": "The graph operation to perform"
        },
        "data": {"type": "string", "description": "Data to add to graph"},
        "query": {"type": "string", "description": "Search query"},
        "user_id": {"type": "string", "description": "User ID filter"},
        "agent_id": {"type": "string", "description": "Agent ID filter"},
        "filters": {"type": "object", "description": "Additional filters"},
        "limit": {"type": "integer", "description": "Result limit", "default": 100},
        "threshold": {"type": "number", "description": "Similarity threshold", "default": 0.7}
    },
    "required": ["operation"]
}


class AddGraphOperation(BaseOperationHandler):
    """Handler for adding data to graph"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="add",
            description="Add nodes and relationships to graph memory",
            parameters=[
                ParameterDefinition("data", ParameterType.STRING, "Data to add to graph", required=True),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute add graph operation"""
        graph_client = context.metadata.get("graph_client")
        
        if not graph_client:
            return {"error": "Graph memory not enabled or configured"}
            
        try:
            # Extract entity parameters
            filters = self._build_filters(params)
            
            # Add to graph
            result = graph_client.add(
                data=params["data"],
                filters=filters
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "add",
                "added_entities": result.get("added_entities", []),
                "added_relations": result.get("added_relations", [])
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters from parameters"""
        filters = params.get("filters", {})
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                filters[key] = params[key]
        return filters


class SearchGraphOperation(BaseOperationHandler):
    """Handler for searching graph"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="search",
            description="Search graph relationships using semantic queries",
            parameters=[
                ParameterDefinition("query", ParameterType.STRING, "Search query", required=True),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False),
                ParameterDefinition("limit", ParameterType.INTEGER, "Result limit", required=False, default=100),
                ParameterDefinition("threshold", ParameterType.FLOAT, "Similarity threshold", required=False, default=0.7)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute search graph operation"""
        graph_client = context.metadata.get("graph_client")
        
        if not graph_client:
            return {"error": "Graph memory not enabled or configured"}
            
        try:
            # Extract filters
            filters = self._build_filters(params)
            
            # Search graph
            result = graph_client.search(
                query=params["query"],
                filters=filters,
                limit=params.get("limit", 100),
                threshold=params.get("threshold", 0.7)
            )
            
            return {
                "status": "success",
                "data": result,
                "operation": "search",
                "query": params["query"],
                "relationships": result.get("relationships", []),
                "count": len(result.get("relationships", []))
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters from parameters"""
        filters = params.get("filters", {})
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                filters[key] = params[key]
        return filters


class GetAllGraphOperation(BaseOperationHandler):
    """Handler for getting all graph data"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="get_all",
            description="Retrieve all graph data",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute get all graph operation"""
        graph_client = context.metadata.get("graph_client")
        
        if not graph_client:
            return {"error": "Graph memory not enabled or configured"}
            
        try:
            # Extract filters
            filters = self._build_filters(params)
            
            # Get all graph data
            result = graph_client.get_all(filters=filters)
            
            return {
                "status": "success",
                "data": result,
                "operation": "get_all",
                "nodes": result.get("nodes", []),
                "edges": result.get("edges", []),
                "node_count": len(result.get("nodes", [])),
                "edge_count": len(result.get("edges", []))
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters from parameters"""
        filters = params.get("filters", {})
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                filters[key] = params[key]
        return filters


class DeleteAllGraphOperation(BaseOperationHandler):
    """Handler for clearing graph data"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="delete_all",
            description="Clear all graph data",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute delete all graph operation"""
        graph_client = context.metadata.get("graph_client")
        
        if not graph_client:
            return {"error": "Graph memory not enabled or configured"}
            
        try:
            # Extract filters
            filters = self._build_filters(params)
            
            # Delete graph data
            result = graph_client.delete_all(filters=filters)
            
            return {
                "status": "success",
                "data": result,
                "operation": "delete_all",
                "message": "Graph data cleared successfully"
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters from parameters"""
        filters = params.get("filters", {})
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                filters[key] = params[key]
        return filters


class VisualizeGraphOperation(BaseOperationHandler):
    """Handler for visualizing graph data"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="visualize",
            description="Generate visualization data for the graph",
            parameters=[
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False),
                ParameterDefinition("agent_id", ParameterType.STRING, "Agent ID filter", required=False),
                ParameterDefinition("filters", ParameterType.OBJECT, "Additional filters", required=False)
            ]
        )
        
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        """Execute visualize graph operation"""
        graph_client = context.metadata.get("graph_client")
        
        if not graph_client:
            return {"error": "Graph memory not enabled or configured"}
            
        try:
            # Extract filters
            filters = self._build_filters(params)
            
            # Get graph data
            graph_data = graph_client.get_all(filters=filters)
            
            # Generate visualization format
            visualization = {
                "nodes": [
                    {
                        "id": node.get("id"),
                        "label": node.get("label", node.get("id")),
                        "type": node.get("type", "default"),
                        "properties": node.get("properties", {})
                    }
                    for node in graph_data.get("nodes", [])
                ],
                "edges": [
                    {
                        "source": edge.get("source"),
                        "target": edge.get("target"),
                        "label": edge.get("label", ""),
                        "type": edge.get("type", "default"),
                        "properties": edge.get("properties", {})
                    }
                    for edge in graph_data.get("edges", [])
                ]
            }
            
            return {
                "status": "success",
                "data": visualization,
                "operation": "visualize",
                "node_count": len(visualization["nodes"]),
                "edge_count": len(visualization["edges"])
            }
            
        except Exception as e:
            return await self.handle_error(context, e)
            
    def _build_filters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build filters from parameters"""
        filters = params.get("filters", {})
        for key in ["user_id", "agent_id"]:
            if key in params and params[key]:
                filters[key] = params[key]
        return filters


# Factory function to get built-in operations
def get_builtin_operations() -> Dict[str, BaseOperationHandler]:
    """Get all built-in graph operations"""
    return {
        "add": AddGraphOperation(),
        "search": SearchGraphOperation(),
        "get_all": GetAllGraphOperation(),
        "delete_all": DeleteAllGraphOperation(),
        "visualize": VisualizeGraphOperation()
    }