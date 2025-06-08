"""
Mem0 MCP Server - Backward Compatible Entry Point

This maintains compatibility with the original 3-tool interface while
providing access to the new extensible architecture.
"""

import os
import sys
import argparse

# Check if we should use the enhanced implementation
USE_ENHANCED = os.environ.get("MEM0_MCP_ENHANCED", "false").lower() == "true"

if USE_ENHANCED or "--enhanced" in sys.argv:
    # Use the enhanced implementation
    from main_enhanced import main
    if __name__ == "__main__":
        # Remove --enhanced from argv if present
        if "--enhanced" in sys.argv:
            sys.argv.remove("--enhanced")
        main()
else:
    # Use the original FastMCP implementation
    from mcp.server.fastmcp import FastMCP
    from mem0 import MemoryClient
    from dotenv import load_dotenv
    import json

    load_dotenv()

    # Initialize mem0 client during module import
    print("Initializing mem0 client...")
    try:
        mem0_client = MemoryClient()
        CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  

- Code Snippets: Save the actual code for future reference.  
- Explanation: Document a clear description of what the code does and how it works.
- Related Technical Details: Include information about the programming language, dependencies, and system specifications.  
- Key Features: Highlight the main functionalities and important aspects of the snippet.
"""
        mem0_client.update_project(custom_instructions=CUSTOM_INSTRUCTIONS)
        print("mem0 client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize mem0 client: {e}")
        raise

    DEFAULT_USER_ID = "cursor_mcp"

    # Initialize FastMCP server
    mcp = FastMCP("mem0-mcp")

    @mcp.tool(
        description="""Add a new coding preference to mem0. This tool stores code snippets, implementation details,
        and coding patterns for future reference. Store every code snippet. When storing code, you should include:
        - Complete code with all necessary imports and dependencies
        - Language/framework version information (e.g., "Python 3.9", "React 18")
        - Full implementation context and any required setup/configuration
        - Detailed comments explaining the logic, especially for complex sections
        - Example usage or test cases demonstrating the code
        - Any known limitations, edge cases, or performance considerations
        - Related patterns or alternative approaches
        - Links to relevant documentation or resources
        - Environment setup requirements (if applicable)
        - Error handling and debugging tips
        The preference will be indexed for semantic search and can be retrieved later using natural language queries."""
    )
    async def add_coding_preference(text: str) -> str:
        """Add a new coding preference to mem0.

        This tool is designed to store code snippets, implementation patterns, and programming knowledge.
        All preferences are automatically enriched with metadata and indexed for semantic search.

        Args:
            text: The coding preference to store. This should include the complete code snippet
                  along with comprehensive context as described in the tool description.

        Returns:
            str: Success message with the memory ID, or error message if the operation fails.
        """
        try:
            # Add to memory for the default user
            result = mem0_client.add(text, user_id=DEFAULT_USER_ID, output_format="v1.1")
            
            # Extract memory ID from the result
            if result and 'memory' in result:
                memory_id = result['memory'].get('id', 'unknown')
                return f"Successfully added coding preference with memory ID: {memory_id}"
            else:
                return "Coding preference added successfully"
                
        except Exception as e:
            return f"Error adding coding preference: {str(e)}"

    @mcp.tool(
        description="""Retrieve all stored coding preferences from mem0. Use this when you need to:
        - Review all previously stored code snippets and patterns
        - Analyze coding patterns and practices across different implementations
        - Find specific implementations when you're not sure of the exact keywords
        - Get a comprehensive overview of stored programming knowledge
        - Ensure you haven't missed any relevant code that was previously saved
        This returns all memories without filtering, which is useful for comprehensive analysis."""
    )
    async def get_all_coding_preferences() -> str:
        """Retrieve all coding preferences stored in mem0.

        This provides a complete view of all stored coding knowledge without any filtering.
        Useful for comprehensive reviews and ensuring no relevant information is missed.

        Returns:
            str: JSON formatted list of all coding preferences with their metadata,
                 or error message if retrieval fails.
        """
        try:
            # Get all memories for the default user
            memories = mem0_client.get_all(user_id=DEFAULT_USER_ID, output_format="v1.1")
            
            if memories:
                # Format the response for better readability
                formatted_memories = []
                for memory in memories:
                    formatted_memory = {
                        "id": memory.get("id", "unknown"),
                        "content": memory.get("text", ""),
                        "metadata": memory.get("metadata", {}),
                        "created_at": memory.get("created_at", "")
                    }
                    formatted_memories.append(formatted_memory)
                
                return json.dumps(formatted_memories, indent=2)
            else:
                return "No coding preferences found"
                
        except Exception as e:
            return f"Error retrieving coding preferences: {str(e)}"

    @mcp.tool(
        description="""Search for specific coding preferences using semantic search. Use this to find:
        - Code implementations for specific features or problems
        - Programming patterns for particular languages or frameworks
        - Best practices and conventions you've previously stored
        - Setup instructions or configuration examples
        - Solutions to specific technical challenges
        The search is semantic, so it understands context and meaning, not just keywords."""
    )
    async def search_coding_preferences(query: str) -> str:
        """Search for coding preferences using semantic search.

        This uses vector similarity to find the most relevant coding preferences based on
        the meaning and context of your query, not just keyword matching.

        Args:
            query: Natural language description of what you're looking for.
                   Can be a problem description, feature name, technology stack, etc.

        Returns:
            str: JSON formatted list of relevant coding preferences sorted by relevance,
                 or error message if search fails.
        """
        try:
            # Search memories for the default user
            results = mem0_client.search(query, user_id=DEFAULT_USER_ID, output_format="v1.1")
            
            if results:
                # Format the search results
                formatted_results = []
                for result in results:
                    formatted_result = {
                        "id": result.get("id", "unknown"),
                        "content": result.get("text", ""),
                        "metadata": result.get("metadata", {}),
                        "relevance_score": result.get("score", 0)
                    }
                    formatted_results.append(formatted_result)
                
                return json.dumps(formatted_results, indent=2)
            else:
                return f"No coding preferences found matching: {query}"
                
        except Exception as e:
            return f"Error searching coding preferences: {str(e)}"

    if __name__ == "__main__":
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Mem0 MCP Server')
        parser.add_argument('--host', type=str, help='Host to bind to (ignored for SSE)')
        parser.add_argument('--port', type=int, help='Port to bind to (ignored for SSE)')
        args = parser.parse_args()
        
        # Note: FastMCP with SSE transport ignores host/port arguments
        # The server will always run on 0.0.0.0:8000 by default
        print("Starting Mem0 MCP Server (Classic Mode)...")
        print("Server will be available at http://0.0.0.0:8000/sse")
        print("To use enhanced mode with 7 tools and plugin support, run with --enhanced flag")
        
        mcp.run(transport="sse")