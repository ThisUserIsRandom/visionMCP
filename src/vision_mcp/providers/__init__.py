"""Provider factory: turns a :class:`ServerConfig` into a :class:`VisionProvider`."""

from __future__ import annotations

from vision_mcp.config import ServerConfig
from vision_mcp.providers.anthropic_provider import AnthropicProvider
from vision_mcp.providers.base import VisionProvider, VisionProviderError, VisionRequest
from vision_mcp.providers.ollama_provider import OllamaProvider
from vision_mcp.providers.openai_provider import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "VisionProvider",
    "VisionProviderError",
    "VisionRequest",
    "create_provider",
]


def create_provider(config: ServerConfig) -> VisionProvider:
    """Instantiate the vision provider for the configured provider name."""
    common = {
        "api_key": config.effective_api_key(),
        "api_url": config.api_url,
        "model": config.model,
        "request_timeout": config.request_timeout_seconds,
        "max_output_tokens": config.max_output_tokens,
        "image_detail": config.image_detail,
    }
    if config.provider == "anthropic":
        return AnthropicProvider(**common)
    if config.provider == "ollama":
        return OllamaProvider(**common)
    if config.provider == "openai":
        return OpenAIProvider(**common)
    raise ValueError(f"Unsupported provider: {config.provider!r}")  # pragma: no cover
