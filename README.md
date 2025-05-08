# framegrab-mcp-server

## Overview
A Model Context Protocol (MCP) server for capturing images from cameras and video streams. Uses the [framegrab](https://github.com/groundlight/framegrab) library to handle the actual image capture.

This MCP server is still in early development. The functionality and available tools are subject to change and expansion as we continue to develop and improve the server.

### Tools
The following tools are available in the Framegrab MCP server:

- **list_framegrabbers**: List all available framegrabbers by name, sorted alphanumerically.
- **grab_frame**: Grab a frame from the specified framegrabber and return it as an image.
- **get_config**: Retrieve the configuration of a specific framegrabber.
- **set_config**: Update the configuration options for a specific framegrabber.
- **create_grabber**: Create a new framegrabber from configuration and add it to the available grabbers.
- **release_grabber**: Release a framegrabber and remove it from the available grabbers.


## Configuration

Currently the server is set up by cloning this repository to your local machine.
```bash
git clone https://github.com/groundlight/framegrab-mcp-server.git
```

Proceed to configure the server for your LLM client.

### Usage with Claude Desktop
Add this to your claude_desktop_config.json:
```json
{
  "mcpServers": {
    "framegrab": {
      "command": "/Users/your_user/.cargo/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "framegrab>=0.11.1",
        "--with",
        "opencv-python",
        "--with",
        "pypylon",
        "mcp",
        "run",
        "/path/to/framegrab-mcp-server/framegrab_mcp_server.py"
      ]
    }
  }
}
```

### Usage with Zed
Add the following to your zed `settings.json`:
```json
{
  "context_servers": {
    "framegrab": {
      "command": {
        "path": "/Users/your_user/.cargo/bin/uv",
        "args": [
          "run",
          "--with",
          "mcp[cli]",
          "--with",
          "framegrab>=0.11.1",
          "--with",
          "opencv-python",
          "--with",
          "pypylon",
          "mcp",
          "run",
          "/path/to/framegrab-mcp-server/framegrab_mcp_server.py"
        ]
      }
    }
  }
}
```
