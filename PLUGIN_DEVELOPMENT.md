# Plugin Development Guide

This guide explains how to create plugins for the extensible Mem0 MCP Server.

## Plugin Types

The Mem0 MCP Server supports several types of plugins:

### 1. Operation Plugins
Add new operations to existing tools.

```python
from mem0_mcp.core.base_plugin import OperationPlugin, PluginMetadata
from mem0_mcp.core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType

class MyCustomOperation(BaseOperationHandler):
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="my_operation",
            description="My custom operation",
            parameters=[
                ParameterDefinition("param1", ParameterType.STRING, "Description", required=True)
            ]
        )
    
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        # Implementation
        return {"status": "success", "result": "data"}

class MyOperationPlugin(OperationPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_operation_plugin",
            version="1.0.0",
            description="Adds custom operations"
        )
    
    async def setup(self) -> None:
        pass
    
    def get_operations(self) -> Dict[str, BaseOperationHandler]:
        return {
            "my_operation": MyCustomOperation()
        }
    
    def get_tool_name(self) -> str:
        return "mem0_memory"  # Tool to extend
```

### 2. Tool Plugins
Add entirely new tools to the server.

```python
from mem0_mcp.core.base_plugin import ToolPlugin

class MyToolPlugin(ToolPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_tool",
            version="1.0.0",
            description="My custom tool"
        )
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "my_tool",
            "description": "My custom tool description",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"}
                }
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        return {"status": "success", "action": action}
```

### 3. Backend Plugins
Provide alternative backend implementations.

```python
from mem0_mcp.core.base_plugin import BackendPlugin

class MyBackendPlugin(BackendPlugin[MyClient]):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my_backend",
            version="1.0.0",
            description="Custom backend implementation"
        )
    
    def get_backend_type(self) -> str:
        return "graph"  # or "vector", "storage", etc.
    
    def get_backend_name(self) -> str:
        return "my_backend"
    
    def create_client(self, **kwargs) -> MyClient:
        return MyClient(self.config)
```

### 4. Middleware Plugins
Process requests and responses.

```python
from mem0_mcp.core.base_plugin import MiddlewarePlugin

class MyMiddlewarePlugin(MiddlewarePlugin):
    async def process_request(self, tool_name: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Modify request
        params["processed"] = True
        return params
    
    async def process_response(self, tool_name: str, operation: str, response: Dict[str, Any]) -> Dict[str, Any]:
        # Modify response
        response["middleware"] = "processed"
        return response
    
    def get_priority(self) -> int:
        return 50  # Lower = higher priority
```

## Plugin Installation

### 1. Directory-based Plugins
Place your plugin file in a plugin directory:

```
custom_plugins/
├── my_plugin.py
├── another_plugin.py
└── __init__.py
```

Configure the path in `mem0-config.yaml`:
```yaml
plugins:
  paths:
    - ./custom_plugins
```

### 2. Module-based Plugins
Install as a Python package and configure:

```yaml
plugins:
  modules:
    - my_plugin_package
```

### 3. Built-in Registration
For development, register directly in code:

```python
from mem0_mcp import Mem0MCPServer
from my_plugin import MyPlugin

server = Mem0MCPServer()
server.add_plugin(MyPlugin)
```

## Plugin Configuration

Plugins can access configuration through `self.config`:

```yaml
plugins:
  config:
    my_plugin:
      option1: value1
      option2: value2
```

```python
class MyPlugin(BasePlugin):
    async def setup(self) -> None:
        option1 = self.config.get("option1")
        # Use configuration
```

## Best Practices

### 1. Error Handling
Always handle errors gracefully:

```python
async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
    try:
        # Operation logic
        return {"status": "success", "data": result}
    except SpecificError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return await self.handle_error(context, e)
```

### 2. Async Support
Use async/await for I/O operations:

```python
async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
    client = context.metadata.get("client")
    result = await client.async_operation()
    return {"status": "success", "data": result}
```

### 3. Parameter Validation
Define clear parameter schemas:

```python
@property
def metadata(self) -> OperationMetadata:
    return OperationMetadata(
        name="operation",
        parameters=[
            ParameterDefinition(
                name="email",
                type=ParameterType.STRING,
                description="User email",
                required=True,
                validation=lambda v: "@" in v
            )
        ]
    )
```

### 4. Event Integration
Use the event bus for decoupled communication:

```python
async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
    event_bus = context.metadata.get("event_bus")
    
    # Emit event
    await event_bus.emit("custom.event", {
        "data": "value"
    })
    
    return {"status": "success"}
```

### 5. Dependency Injection
Use the DI container for dependencies:

```python
from mem0 import AsyncMemoryClient

async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
    # Get injected client
    client = context.metadata.get("client")
    
    # Or resolve from container
    container = context.metadata.get("container")
    client = await container.resolve(AsyncMemoryClient)
    
    return {"status": "success"}
```

## Example: Complete Plugin

Here's a complete example of a plugin that adds sentiment analysis to memories:

```python
from typing import Any, Dict
from mem0_mcp.core.base_plugin import OperationPlugin, PluginMetadata
from mem0_mcp.core.base_operation import BaseOperationHandler, OperationMetadata, ParameterDefinition, ParameterType, OperationContext

class SentimentAnalysisOperation(BaseOperationHandler):
    """Analyze sentiment of memories"""
    
    @property
    def metadata(self) -> OperationMetadata:
        return OperationMetadata(
            name="analyze_sentiment",
            description="Analyze sentiment of memories",
            parameters=[
                ParameterDefinition("memory_ids", ParameterType.ARRAY, "Memory IDs to analyze", required=False),
                ParameterDefinition("user_id", ParameterType.STRING, "User ID filter", required=False)
            ]
        )
    
    async def execute(self, context: OperationContext, **params) -> Dict[str, Any]:
        from mem0 import AsyncMemoryClient
        
        client = context.metadata.get("client")
        if not client:
            return {"error": "Memory client not initialized"}
        
        # Get memories
        if params.get("memory_ids"):
            memories = []
            for memory_id in params["memory_ids"]:
                memory = await client.get(memory_id=memory_id)
                memories.append(memory)
        else:
            result = await client.get_all(user_id=params.get("user_id"))
            memories = result.get("results", [])
        
        # Analyze sentiment (mock implementation)
        sentiments = []
        for memory in memories:
            text = memory.get("memory", "")
            # In real implementation, use sentiment analysis library
            sentiment = self._analyze_text(text)
            sentiments.append({
                "memory_id": memory.get("id"),
                "sentiment": sentiment,
                "confidence": 0.85
            })
        
        return {
            "status": "success",
            "data": sentiments,
            "operation": "analyze_sentiment",
            "count": len(sentiments)
        }
    
    def _analyze_text(self, text: str) -> str:
        """Mock sentiment analysis"""
        positive_words = ["good", "great", "excellent", "happy", "love"]
        negative_words = ["bad", "terrible", "hate", "awful", "sad"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"


class SentimentAnalysisPlugin(OperationPlugin):
    """Plugin that adds sentiment analysis to memory operations"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sentiment_analysis",
            version="1.0.0",
            description="Adds sentiment analysis capabilities to memory management",
            author="Your Name",
            capabilities=["sentiment_analysis", "nlp"],
            config_schema={
                "model": {"type": "string", "default": "basic"},
                "threshold": {"type": "number", "default": 0.7}
            }
        )
    
    async def setup(self) -> None:
        """Initialize sentiment analysis model"""
        model = self.config.get("model", "basic")
        if model != "basic":
            # Load actual sentiment analysis model
            pass
    
    def get_operations(self) -> Dict[str, BaseOperationHandler]:
        """Return sentiment analysis operations"""
        return {
            "analyze_sentiment": SentimentAnalysisOperation()
        }
    
    def get_tool_name(self) -> str:
        """This plugin extends the mem0_advanced tool"""
        return "mem0_advanced"
```

## Testing Your Plugin

Create a test file:

```python
import asyncio
from mem0_mcp import Mem0MCPServer
from my_plugin import MyPlugin

async def test_plugin():
    # Create server
    server = Mem0MCPServer()
    
    # Add plugin
    server.add_plugin(MyPlugin)
    
    # Initialize
    await server.initialize()
    
    # Test operation
    result = await server._tool_handlers["my_tool"](
        operation="my_operation",
        param1="test"
    )
    
    print(result)

asyncio.run(test_plugin())
```

## Plugin Distribution

### 1. PyPI Package
Create a package structure:

```
my-mem0-plugin/
├── setup.py
├── README.md
├── my_mem0_plugin/
│   ├── __init__.py
│   └── plugin.py
└── tests/
    └── test_plugin.py
```

### 2. GitHub Repository
Share your plugin:

```markdown
# My Mem0 Plugin

## Installation
```bash
pip install my-mem0-plugin
```

## Configuration
Add to `mem0-config.yaml`:
```yaml
plugins:
  modules:
    - my_mem0_plugin
```
```

## Advanced Topics

### 1. Composite Plugins
Create plugins that contain multiple sub-plugins:

```python
from mem0_mcp.core.base_plugin import CompositePlugin

class MyPluginSuite(CompositePlugin):
    async def setup(self) -> None:
        self.add_plugin(Plugin1())
        self.add_plugin(Plugin2())
        self.add_plugin(Plugin3())
        await super().setup()
```

### 2. Hot Reloading
Plugins can be reloaded without restarting:

```python
await server.plugin_registry.reload_plugin("my_plugin")
```

### 3. Plugin Dependencies
Declare dependencies between plugins:

```python
@property
def metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="my_plugin",
        version="1.0.0",
        dependencies=["other_plugin", "base_plugin"]
    )
```

### 4. Custom Events
Create and handle custom events:

```python
# Emit custom event
await event_bus.emit("my_plugin.custom_event", {
    "data": "value"
})

# Subscribe to events
@event_bus.on("my_plugin.custom_event")
async def handle_custom_event(event):
    print(f"Received: {event.data}")
```

## Conclusion

The Mem0 MCP Server's plugin architecture provides extensive flexibility for extending functionality. By following these patterns and best practices, you can create powerful plugins that integrate seamlessly with the core system.