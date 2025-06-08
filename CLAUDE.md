# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that integrates with Mem0 for managing coding preferences. The server provides tools for storing, retrieving, and searching coding patterns and implementation details through an SSE-based API endpoint that can be used with Cursor and other MCP-compatible tools.

## Development Commands

### Python Environment Setup
```bash
# Initialize uv environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies in editable mode
uv pip install -e .
```

### Running the Server
```bash
# Start single instance (SSE server on default port 8000)
uv run main.py

# For multiple instances using PM2
pm2 start ecosystem.config.js

# For manual scaling
./scale.sh start 4    # Start 4 instances on ports 8080-8083
./scale.sh stop       # Stop all instances
./scale.sh status     # Check instance status
```

### Node.js Package (if using npm distribution)
```bash
cd node/mem0
npm run build   # Build TypeScript
npm run dev     # Development with watch mode
npm start       # Run built version
```

### Testing & Linting (Mem0 core library)
```bash
cd mem0
hatch run test    # Run tests
hatch run format  # Format code with ruff
hatch run lint    # Lint code
```

## Architecture

### Core Components

1. **MCP Server (`main.py`)**: FastMCP-based server that exposes three tools via SSE transport:
   - `add_coding_preference`: Stores code snippets with comprehensive context
   - `get_all_coding_preferences`: Retrieves all stored preferences
   - `search_coding_preferences`: Semantic search through stored preferences

2. **Mem0 Integration**: Uses the Mem0 memory client for persistent storage with custom instructions for extracting:
   - Code snippets
   - Technical explanations
   - Dependencies and specifications
   - Key features

3. **Transport Layer**: SSE (Server-Sent Events) endpoint at `/sse` for real-time communication with MCP clients like Cursor

### Scaling Architecture

The project supports multiple scaling approaches:

1. **PM2 Scaling**: Using `ecosystem.config.js` for process management with automatic restart and health checks
2. **Manual Scaling**: Using `scale.sh` script for running multiple instances on different ports
3. **Gunicorn**: Configuration available for production deployment with worker processes

### Key Design Decisions

- **SSE Transport**: Chosen for cloud-native deployments where server and clients can be decoupled processes
- **Default User ID**: Uses "cursor_mcp" as the default user for all memory operations
- **Custom Instructions**: Predefined extraction template ensures consistent memory storage format
- **Port Configuration**: SSE server ignores host/port arguments and uses default settings (0.0.0.0:8000)

## Environment Variables

Required in `.env` file:
- `MEM0_API_KEY`: Your Mem0 API key for authentication

## Integration Points

- **Cursor Integration**: Connect to `http://0.0.0.0:8000/sse` in Cursor's MCP settings
- **MCP Protocol**: Follows Model Context Protocol standards for tool definitions and responses
- **Mem0 API**: Uses Mem0's memory client for all storage operations with v1.1 output format