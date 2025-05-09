# framegrab-mcp-server

## Overview
A Model Context Protocol (MCP) server for capturing images from cameras and video streams. Uses the [framegrab](https://github.com/groundlight/framegrab) library to handle the actual image capture.
This server can be used to capture images from a webcam, a USB camera, an RTSP stream, a youtube live stream, or any other video source supported by the framegrab library.

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

### Usage with Claude Desktop
Add this to your claude_desktop_config.json:
```json
{
  "mcpServers": {
    "framegrab": {
      "command": "/Users/your_user/.cargo/bin/uvx",
      "args": [
        "framegrab-mcp-server"
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
        "path": "/Users/your_user/.cargo/bin/uvx",
        "args": [
          "framegrab-mcp-server"
        ]
      }
    }
  }
}
```

### (experimental) Enabling autodiscovery of framegrabbers
Enable autodiscovery of framegrabbers (such as your webcam or usb cameras) by setting
`ENABLE_FRAMEGRAB_AUTO_DISCOVERY="true"` in your environment variables. This will automatically add any discovered framegrabbers to the list of available framegrabbers:

```json
{
  "mcpServers": {
    "framegrab": {
      "command": "/Users/your_user/.cargo/bin/uvx",
      "args": [
        "framegrab-mcp-server"
      ],
      "env": {
        "ENABLE_FRAMEGRAB_AUTO_DISCOVERY": "true"
      }
    }
  }
}
```

This will increase server startup time.