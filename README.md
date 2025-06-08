# MCP Server with Mem0 - Enhanced Edition

This is an enhanced fork of the [original Mem0 MCP server](https://github.com/mem0ai/mem0-mcp) that provides both a simple 3-tool mode for coding preferences and an extended 7-tool mode with 39 operations for comprehensive memory management.

This implementation demonstrates a structured approach for using an [MCP](https://modelcontextprotocol.io/introduction) server with [mem0](https://mem0.ai) to manage memories efficiently. The server can be used with Cursor, Claude Desktop, and other MCP-compatible tools.

## Installation

1. Clone this repository:

```bash
git clone https://github.com/glassBead-tc/mem0-mcp-glassBead.git
cd mem0-mcp-glassBead
```
2. Initialize the `uv` environment:

```bash
uv venv
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install the dependencies using `uv`:

```bash
# Install in editable mode from pyproject.toml
uv pip install -e .
```

5. Update `.env` file in the root directory with your mem0 API key:

```bash
MEM0_API_KEY=your_api_key_here
```

## Usage

1. Start the MCP server:

```bash
uv run main.py
```

2. In Cursor, connect to the SSE endpoint, follow this [doc](https://docs.cursor.com/context/model-context-protocol) for reference:

```
http://0.0.0.0:8080/sse
```

3. Open the Composer in Cursor and switch to `Agent` mode.

## Demo with Cursor

https://github.com/user-attachments/assets/56670550-fb11-4850-9905-692d3496231c

## What's New in This Fork

### Enhanced Mode with 7 Tools
- **39 total operations** across 7 specialized tools
- Clean, simple implementation using FastMCP
- Same reliable architecture as classic mode
- No unnecessary complexity

### Fixed Issues
- Resolved FastMCP parameter handling errors
- Removed complex Starlette/SSE implementations that caused event loop conflicts
- Simplified from broken plugin architecture to working direct implementation

## Features

### Classic Mode (Default)

The server provides three main tools for managing code preferences:

1. `add_coding_preference`: Store code snippets, implementation details, and coding patterns with comprehensive context including:
   - Complete code with dependencies
   - Language/framework versions
   - Setup instructions
   - Documentation and comments
   - Example usage
   - Best practices

2. `get_all_coding_preferences`: Retrieve all stored coding preferences to analyze patterns, review implementations, and ensure no relevant information is missed.

3. `search_coding_preferences`: Semantically search through stored coding preferences to find relevant:
   - Code implementations
   - Programming solutions
   - Best practices
   - Setup guides
   - Technical documentation

### Enhanced Mode (--enhanced flag)

Run with `--enhanced` flag or set `MEM0_MCP_ENHANCED=true` to access all 7 tools with 39 total operations:

```bash
# Using flag
uv run main.py --enhanced --port 8080

# Using environment variable
MEM0_MCP_ENHANCED=true uv run main.py --port 8080
```

Enhanced mode provides the following tools:

1. **mem0_memory**: Core memory operations
   - Operations: add, get, get_all, search, update, delete, delete_all, history, batch_update, batch_delete, feedback
   - Full CRUD operations with batch support
   - Semantic search capabilities
   - Memory history tracking
   
2. **mem0_entity**: Entity management (users, agents, apps)
   - Operations: list_users, create_user, delete_user, migrate_user
   - Manage different entity types
   - Entity-specific memory operations
   
3. **mem0_graph**: Graph-based relationships between memories
   - Operations: add_relation, get_relations, visualize, analyze, remove_relation
   - Build knowledge graphs
   - Analyze memory relationships
   
4. **mem0_export**: Import/export in various formats
   - Operations: export, import, backup, restore
   - Support for JSON format
   - Bulk data operations
   
5. **mem0_config**: Configuration management
   - Operations: get_config, update_config, reset_config, validate_config
   - Manage custom instructions
   - Validate configuration settings
   
6. **mem0_webhook**: Webhook management for events
   - Operations: create, list, update, delete, test
   - Configure event notifications
   - Test webhook connections
   
7. **mem0_advanced**: Analytics and optimization features
   - Operations: analyze_usage, optimize_storage, generate_insights
   - Memory usage analytics
   - Storage optimization recommendations

## Why?

This implementation allows for a persistent coding preferences system that can be accessed via MCP. The SSE-based server can run as a process that agents connect to, use, and disconnect from whenever needed. This pattern fits well with "cloud-native" use cases where the server and clients can be decoupled processes on different nodes.

### Server Details

Both classic and enhanced modes run on the same port with FastMCP's SSE transport:

```bash
# Classic mode (3 tools)
uv run main.py

# Enhanced mode (7 tools, 39 operations)
uv run main.py --enhanced
```

**Note**: FastMCP with SSE transport always runs on `http://0.0.0.0:8000/sse` regardless of port arguments. The `--port` flag is ignored by FastMCP's SSE implementation.

The server exposes an SSE endpoint at `/sse` that MCP clients can connect to for accessing the memory management tools.

### Configuration

The server uses environment variables for configuration:

```bash
# Required
MEM0_API_KEY=your_api_key_here

# Optional - Use enhanced mode by default
MEM0_MCP_ENHANCED=true
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

This project is a fork of the original [mem0ai/mem0-mcp](https://github.com/mem0ai/mem0-mcp) repository. Thanks to the Mem0 team for creating the initial implementation.

## License

This project maintains the same license as the original repository.

