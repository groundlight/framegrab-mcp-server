.PHONY: mcp-inspector

mcp-inspector:  # Run the MCP inspector
	uv run mcp dev framegrab_mcp_server.py

run-server:  # Run the server locally
	uv run framegrab-mcp-server
