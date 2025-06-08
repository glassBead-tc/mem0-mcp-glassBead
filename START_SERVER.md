# Starting the Extensible Mem0 MCP Server

## Quick Start

1. Navigate to this directory:
```bash
cd /Users/b.c.nims/glassBead-local-mcp/mem0-mcp/trees/enhanced-mem0-tools-3
```

2. Activate the virtual environment:
```bash
source .venv/bin/activate
```

3. Start the server:
```bash
python main.py --port 8080 --debug
```

The server will start on `http://localhost:8080` with the following endpoints:
- `/sse` - SSE endpoint for MCP communication
- `/health` - Health check endpoint
- `/info` - Server information and loaded plugins
- `/messages/` - Message handling endpoint

## Testing All Operations

Once the server is running, in a new terminal:

```bash
cd /Users/b.c.nims/glassBead-local-mcp/mem0-mcp/trees/enhanced-mem0-tools-3
source .venv/bin/activate
python test_all_operations.py
```

This will test all 7 tools and their operations:
1. **mem0_memory** - All memory CRUD operations
2. **mem0_entity** - Entity management
3. **mem0_graph** - Graph memory operations
4. **mem0_export** - Export/import functionality
5. **mem0_config** - Configuration management
6. **mem0_webhook** - Webhook operations (enterprise)
7. **mem0_advanced** - Multimodal and analytics

## Connect to Cursor

To connect this server to Cursor, use the SSE endpoint:
```
http://localhost:8080/sse
```

## Features of This Implementation

- **Plugin System**: Dynamically load custom plugins
- **Event Bus**: React to memory operations with event handlers
- **Caching**: Optional caching via plugin
- **Logging**: Comprehensive logging middleware
- **Extensible**: Add new operations without modifying core code
- **Type Safe**: Full type hints and validation

## Loaded Plugins

The following plugins are loaded by default:
- `logging_middleware` - Logs all operations
- `cache_plugin` - Caches read operations
- `batch_operations` - Adds batch update/delete
- `feedback_operations` - Memory feedback system
- `history_operations` - Memory history tracking
- `neo4j_backend` - Graph backend (if configured)

## Custom Extensions

To add custom functionality, create plugins in the `custom_plugins/` directory.
See `PLUGIN_DEVELOPMENT.md` for details.