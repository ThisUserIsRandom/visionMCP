"""visionMCP package.

An MCP server that acts as the "eyes" of a larger reasoning LLM. It exposes
image-understanding tools backed by a vision-capable model served through
Ollama, OpenAI, or Anthropic.
"""

from __future__ import annotations

__version__ = "0.1.0"

from vision_mcp.config import ConfigError, ServerConfig, load_config
from vision_mcp.server import build_server

__all__ = [
    "ConfigError",
    "ServerConfig",
    "build_server",
    "load_config",
    "__version__",
]
