.PHONY: install-server mcp-inspector

install-server:  # Install the Groundlight server in Claude Desktop
	uv run mcp install framegrab_mcp_server.py --name "framegrab"

mcp-inspector:  # Run the MCP inspector
	uv run mcp dev framegrab_mcp_server.py
