"""FastMCP server definition: the "eyes" of a larger reasoning LLM.

Exposes image-understanding tools (describe, ask, OCR, compare) that any MCP
client — including a bigger reasoning LLM — can call. Backed by Ollama, OpenAI,
or Anthropic, chosen at runtime via ``config.json``.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from vision_mcp.config import ServerConfig
from vision_mcp.images import EncodedImage, encode_image
from vision_mcp.providers import (
    VisionProvider,
    VisionRequest,
    create_provider,
)

# ---------------------------------------------------------------------------
# Prompt templates (injected as the user message on top of the default prompt)
# ---------------------------------------------------------------------------

DESCRIBE_PROMPT = (
    "Describe the image in detail. Cover the main subject, scene, objects, "
    "people, animals, colors, layout, and any notable details you can see."
)

EXTRACT_TEXT_PROMPT = (
    "Transcribe ALL legible text visible in the image, preserving the original "
    "language and as much of the reading order and layout as possible. "
    "If there is no text, say so explicitly."
)

DEFAULT_COMPARE_QUESTION = (
    "Describe the key similarities and differences between these two images."
)


def _encode(source: str, cfg: ServerConfig) -> EncodedImage:
    return encode_image(
        source,
        max_image_mb=cfg.max_image_mb,
        max_image_dimension=cfg.max_image_dimension,
        jpeg_quality=cfg.jpeg_quality,
        url_timeout=cfg.request_timeout_seconds,
    )


class VisionMCPServer:
    """Wraps the provider so tools can be wired onto a FastMCP server."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.provider: VisionProvider = create_provider(config)

    def _request(
        self,
        images: list[EncodedImage],
        prompt: str,
        detail: str | None = None,
    ) -> VisionRequest:
        return VisionRequest(
            images=[(img.base64, img.media_type) for img in images],
            prompt=prompt,
            system_prompt=self.config.default_prompt,
            max_tokens=self.config.max_output_tokens,
            timeout=self.config.request_timeout_seconds,
            image_detail=detail or self.config.image_detail,
        )

    def _image_summary(self, images: list[EncodedImage]) -> dict[str, Any]:
        return [
            {
                "width": img.width,
                "height": img.height,
                "media_type": img.media_type,
                "source": img.source_kind,
                "final_kb": round(img.final_bytes / 1024, 1),
                "resized": img.resized,
            }
            for img in images
        ]

    # -- tool implementations --------------------------------------------

    def describe(self, image: str, detail: str = "auto") -> str:
        img = _encode(image, self.config)
        request = self._request([img], DESCRIBE_PROMPT, detail=detail)
        answer = self.provider.generate(request)
        return json.dumps(
            {"answer": answer, "image": self._image_summary([img])[0]},
            ensure_ascii=False,
            indent=2,
        )

    def ask(self, image: str, question: str) -> str:
        img = _encode(image, self.config)
        request = self._request([img], question)
        answer = self.provider.generate(request)
        return json.dumps(
            {"answer": answer, "image": self._image_summary([img])[0]},
            ensure_ascii=False,
            indent=2,
        )

    def extract_text(self, image: str) -> str:
        img = _encode(image, self.config)
        request = self._request([img], EXTRACT_TEXT_PROMPT)
        answer = self.provider.generate(request)
        return json.dumps(
            {"answer": answer, "image": self._image_summary([img])[0]},
            ensure_ascii=False,
            indent=2,
        )

    def compare(self, image_a: str, image_b: str, question: str | None = None) -> str:
        img_a = _encode(image_a, self.config)
        img_b = _encode(image_b, self.config)
        prompt = f"{question or DEFAULT_COMPARE_QUESTION}\n\n"
        prompt += "Image A is the first image above; Image B is the second."
        request = self._request([img_a, img_b], prompt)
        answer = self.provider.generate(request)
        return json.dumps(
            {
                "answer": answer,
                "image_a": self._image_summary([img_a])[0],
                "image_b": self._image_summary([img_b])[0],
            },
            ensure_ascii=False,
            indent=2,
        )

    def status(self) -> dict[str, Any]:
        return self.config.public_dict()


def build_server(config: ServerConfig) -> FastMCP:
    """Build and return a configured FastMCP server instance."""
    config.validate()
    handler = VisionMCPServer(config)
    server = FastMCP(name=config.server_name)

    @server.tool
    def describe_image(
        image: str,
        detail: str = "auto",
    ) -> str:
        """Describe an image in natural language.

        `image` can be a local file path, an http(s) URL, or a base64 data URI
        (data:image/png;base64,...). `detail` (OpenAI/Ollama) controls image
        resolution sent to the model: 'auto', 'low', or 'high'.
        """
        return handler.describe(image, detail)

    @server.tool
    def ask_about_image(image: str, question: str) -> str:
        """Ask a specific question about an image and get a focused answer."""
        return handler.ask(image, question)

    @server.tool
    def extract_text(image: str) -> str:
        """Transcribe / OCR all legible text in an image."""
        return handler.extract_text(image)

    @server.tool
    def compare_images(
        image_a: str,
        image_b: str,
        question: str | None = None,
    ) -> str:
        """Compare two images side by side and answer a question about them."""
        return handler.compare(image_a, image_b, question)

    @server.tool
    def server_status() -> dict[str, Any]:
        """Return the active provider, model, transport, and limits (no secrets)."""
        return handler.status()

    @server.resource("config://visionMCP/status")
    def status_resource() -> str:
        """Read-only view of the current provider/model configuration."""
        return json.dumps(handler.status(), indent=2, ensure_ascii=False)

    return server


__all__ = ["build_server"]
