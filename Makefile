.PHONY: mcp-inspector

mcp-inspector:  # Run the MCP inspector
	uv run mcp dev framegrab_mcp_server.py

run-server:  # Run the server locally
	uv run framegrab_mcp_server.py

clean:
	rm -rf dist

build: clean
	uv build --no-sources

publish:
	uv publish
