"""Anthropic (Claude) vision provider."""

from __future__ import annotations

from typing import Any

from anthropic import Anthropic
from anthropic import APIError as AnthropicAPIError

from vision_mcp.providers.base import VisionProvider, VisionProviderError, VisionRequest


def _build_content(request: VisionRequest) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64_data},
        }
        for base64_data, media_type in request.images
    ]
    content.append({"type": "text", "text": request.prompt})
    return content


class AnthropicProvider(VisionProvider):
    """Vision via the Anthropic Messages API (Claude vision models)."""

    def _client(self) -> Anthropic:
        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.request_timeout,
            "max_retries": 2,
        }
        if self.api_url:
            kwargs["base_url"] = self.api_url
        return Anthropic(**kwargs)

    def generate(self, request: VisionRequest) -> str:
        try:
            message = self._client().messages.create(
                model=self.model,
                max_tokens=request.max_tokens or self.max_output_tokens,
                system=request.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": _build_content(request),
                    }
                ],
            )
        except AnthropicAPIError as exc:
            raise VisionProviderError(
                f"Anthropic API error ({exc.status_code}): {exc.message}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - normalise SDK errors
            raise VisionProviderError(f"Anthropic request failed: {exc}") from exc

        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        return text.strip() if text else ""
