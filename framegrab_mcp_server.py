import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

import cv2
from framegrab import FrameGrabber
from mcp.server.fastmcp import FastMCP, Image

logger = logging.getLogger(__name__)

ENABLE_FRAMEGRAB_AUTO_DISCOVERY = (
    os.getenv("ENABLE_FRAMEGRAB_AUTO_DISCOVERY", "false").lower() == "true"
)

# Cache to store created FrameGrabbers, maps name to FrameGrabber
_grabber_cache = {}


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Any]:
    if ENABLE_FRAMEGRAB_AUTO_DISCOVERY:
        logger.info("Autodiscovering generic_usb and basler framegrabbers...")
        try:
            grabbers: dict[str, FrameGrabber] = FrameGrabber.autodiscover()
            logger.info(f"Autodiscovered {len(grabbers)} framegrabbers.")
            _grabber_cache.update(grabbers)
        except Exception:
            logger.error("Error autodiscovering framegrabbers.", exc_info=True)

    logger.info("Framegrab MCP server has started, listening for requests...")

    yield {}

    logger.info("Framegrab MCP server is stopping, releasing framegrabbers...")
    for _, grabber in _grabber_cache.items():
        try:
            grabber.release()
        except Exception as e:
            logger.error(f"Error closing framegrabber {grabber}: {e}")
    logger.info("Done.")


mcp = FastMCP(
    "framegrab-mcp",
    dependencies=[
        "framegrab>=0.11.0",
        "opencv-python",
        "numpy",
        "pypylon",
    ],
    lifespan=app_lifespan,
)


@mcp.tool(
    name="list_framegrabbers",
    description="List all available framegrabbers by name, sorted alphanumerically.",
)
def list_framegrabbers() -> list[str]:
    return sorted(list(_grabber_cache.keys()))


@mcp.tool(
    name="grab_frame",
    description="Grab a frame from the specified framegrabber and return it as an image in the specified format.",
)
def grab_frame(
    framegrabber_name: str, format: Literal["png", "jpg", "webp"] = "webp"
) -> Image:
    grabber: FrameGrabber = _grabber_cache.get(framegrabber_name)
    if not grabber:
        raise ValueError(
            f"Framegrabber with name {framegrabber_name} not found. Options are: {list(_grabber_cache.keys())}."
        )

    frame = grabber.grab()
    if format not in ["png", "jpg", "webp"]:
        raise ValueError("Format must be one of: png, jpg, webp")

    # Convert ndarray to bytes in specified format
    if format == "jpg":
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
        success, buffer = cv2.imencode(f".{format}", frame, encode_params)
    elif format == "png":
        # Use compression level 9 (highest) for PNG to reduce size
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
        success, buffer = cv2.imencode(f".{format}", frame, encode_params)
    elif format == "webp":
        # Use quality 80 for WebP to balance size and quality
        encode_params = [cv2.IMWRITE_WEBP_QUALITY, 80]
        success, buffer = cv2.imencode(f".{format}", frame, encode_params)
    else:
        success, buffer = cv2.imencode(f".{format}", frame)

    if not success:
        raise RuntimeError(f"Failed to encode image as {format.upper()}.")

    # Create MCP Image object from the encoded bytes
    return Image(data=buffer.tobytes(), format=format)


@mcp.tool(
    name="get_config",
    description="Retrieve the configuration of a specific framegrabber.",
)
def get_config(framegrabber_name: str) -> dict:
    grabber: FrameGrabber = _grabber_cache.get(framegrabber_name)
    if not grabber:
        raise ValueError(
            f"Framegrabber with name {framegrabber_name} not found. Options are: {list(_grabber_cache.keys())}."
        )
    return grabber.config


@mcp.tool(
    name="set_config",
    description="Update the configuration options for a specific framegrabber.",
)
def set_config(framegrabber_name: str, options: dict) -> dict:
    grabber: FrameGrabber = _grabber_cache.get(framegrabber_name)
    if not grabber:
        raise ValueError(
            f"Framegrabber with name {framegrabber_name} not found. Options are: {list(_grabber_cache.keys())}."
        )

    try:
        # Update the framegrabber's configuration with the new options
        grabber.apply_options(options)
        logger.info(f"Updated configuration for framegrabber '{framegrabber_name}'")
        return grabber.config
    except Exception as e:
        logger.error(f"Error applying options to {framegrabber_name}: {e}")
        raise ValueError(f"Failed to apply options to framegrabber: {str(e)}")


@mcp.tool(
    name="create_grabber",
    description="""Create a new framegrabber from a configuration dictionary.
    The config should contain at minimum the 'input_type' field, and any other required parameters
    for the specific input type. For example, an RTSP camera needs an 'id' with 'rtsp_url'.
    Examples:
    {
        "name": "My RTSP Camera",
        "input_type": "rtsp",
        "id": {
            "rtsp_url": "rtsp://admin:password@192.168.1.100:554/stream"
        }
    }

    {
        "name": "My Webcam",
        "input_type": "generic_usb",
    }

    Returns the name of the created framegrabber.""",
)
def create_grabber(config: dict) -> str:
    try:
        # Ensure the config has a name to avoid conflicts
        if "name" not in config:
            raise ValueError("The configuration must include a 'name' field.")

        # Check if a grabber with this name already exists
        name = config["name"]
        if name in _grabber_cache:
            raise ValueError(f"A framegrabber with name '{name}' already exists.")

        # Create the new grabber
        grabber = FrameGrabber.create_grabber(config)
        _grabber_cache[name] = grabber
        logger.info(f"Created new framegrabber: {name}")
        return name
    except Exception as e:
        logger.error(f"Error creating framegrabber: {e}")
        raise ValueError(f"Failed to create framegrabber: {str(e)}")


@mcp.tool(
    name="release_grabber",
    description="Release a framegrabber and remove it from the available grabbers.",
)
def release_grabber(framegrabber_name: str) -> bool:
    """
    Release a framegrabber's resources and remove it from the available grabbers.

    Returns True if successful, raises an exception otherwise.
    """
    grabber: FrameGrabber = _grabber_cache.get(framegrabber_name)
    if not grabber:
        raise ValueError(
            f"Framegrabber with name {framegrabber_name} not found. Options are: {list(_grabber_cache.keys())}."
        )

    try:
        grabber.release()
        del _grabber_cache[framegrabber_name]
        logger.info(f"Released framegrabber: {framegrabber_name}")
        return True
    except Exception as e:
        logger.error(f"Error releasing framegrabber {framegrabber_name}: {e}")
        raise ValueError(f"Failed to release framegrabber: {str(e)}")


@mcp.resource(
    uri="fg://framegrabbers",
    name="framegrabbers",
    description="Lists all available framegrabbers by name, sorted alphanumerically.",
    mime_type="application/json",
)
def framegrabbers() -> list[str]:
    return list_framegrabbers()


def main():
    mcp.run()


if __name__ == "__main__":
    main()
