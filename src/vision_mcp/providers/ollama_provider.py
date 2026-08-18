"""Ollama vision provider.

Ollama ships an OpenAI-compatible API at ``http://localhost:11434/v1``, so this
provider reuses :class:`OpenAIProvider` and simply supplies the Ollama defaults
via the configuration layer. Works with any Ollama vision model, e.g.
``llama3.2-vision``, ``qwen2.5vl``, ``llava``, ``minicpm-v``.

First pull a model::

    ollama pull llama3.2-vision
"""

from __future__ import annotations

from vision_mcp.providers.base import VisionRequest
from vision_mcp.providers.openai_provider import OpenAIProvider


class OllamaProvider(OpenAIProvider):
    """Vision via Ollama's OpenAI-compatible endpoint."""

    @property
    def provider_name(self) -> str:
        return "ollama"

    def generate(self, request: VisionRequest) -> str:
        # Ollama is lenient about fake keys; make sure we send something non-empty
        # so the OpenAI SDK doesn't reject the request before it reaches Ollama.
        if not self.api_key:
            self.api_key = "ollama"
        return super().generate(request)
