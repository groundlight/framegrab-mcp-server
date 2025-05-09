import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

import cv2
from framegrab import FrameGrabber
from framegrab.config import (
    BaslerFrameGrabberConfig,
    FileStreamFrameGrabberConfig,
    GenericUSBFrameGrabberConfig,
    HttpLiveStreamingFrameGrabberConfig,
    RealSenseFrameGrabberConfig,
    RTSPFrameGrabberConfig,
    YouTubeLiveFrameGrabberConfig,
)
from mcp.server.fastmcp import FastMCP, Image

logger = logging.getLogger(__name__)

ENABLE_FRAMEGRAB_AUTO_DISCOVERY = (
    os.getenv("ENABLE_FRAMEGRAB_AUTO_DISCOVERY", "false").lower() == "true"
)
FRAMEGRAB_RTSP_AUTO_DISCOVERY_MODE = os.getenv(
    "FRAMEGRAB_RTSP_AUTO_DISCOVERY_MODE",
    "off",  # "off", "ip_only", "light", "complete_fast", "complete_slow"
)

# Cache to store created FrameGrabbers, maps name to FrameGrabber
_grabber_cache = {}


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Any]:
    if ENABLE_FRAMEGRAB_AUTO_DISCOVERY:
        logger.info("Autodiscovering generic_usb and basler framegrabbers...")
        try:
            grabbers: dict[str, FrameGrabber] = FrameGrabber.autodiscover(
                rtsp_discover_mode=FRAMEGRAB_RTSP_AUTO_DISCOVERY_MODE
            )
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
    "framegrab",
    dependencies=[
        "framegrab>=0.11.0",
        "opencv-python",
        "numpy",
        "pypylon",
    ],
    lifespan=app_lifespan,
)


@mcp.tool(
    name="create_framegrabber",
    description="""Create a new framegrabber from a configuration object.
Framegrabbers can be used to capture images from a webcam, a USB camera, an RTSP stream, a youtube live stream, or any other video source supported by the framegrab library.
Returns the name of the created framegrabber.""",
)
def create_framegrabber(
    config: YouTubeLiveFrameGrabberConfig
    | RTSPFrameGrabberConfig
    | GenericUSBFrameGrabberConfig
    | FileStreamFrameGrabberConfig
    | HttpLiveStreamingFrameGrabberConfig
    | RealSenseFrameGrabberConfig
    | BaslerFrameGrabberConfig,
) -> str:
    try:
        # Create the new grabber
        grabber = FrameGrabber.create_grabber(config)
        _grabber_cache[config.name] = grabber
        logger.info(f"Created new framegrabber: {config.name}")
        return config.name
    except Exception as e:
        logger.error(f"Error creating framegrabber: {e}")
        raise ValueError(f"Failed to create framegrabber: {str(e)}")


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
    name="list_framegrabbers",
    description="List all available framegrabbers by name, sorted alphanumerically.",
)
def list_framegrabbers() -> list[str]:
    return sorted(list(_grabber_cache.keys()))


@mcp.tool(
    name="get_framegrabber_config",
    description="Retrieve the configuration of a specific framegrabber.",
)
def get_framegrabber_config(framegrabber_name: str) -> dict:
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
def set_framegrabber_config(framegrabber_name: str, options: dict) -> dict:
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
    name="release_grabber",
    description="Release a framegrabber and remove it from the available grabbers.",
)
def release_framegrabber(framegrabber_name: str) -> bool:
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
