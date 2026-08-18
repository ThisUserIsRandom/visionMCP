"""OpenAI-compatible vision provider.

Used for the ``openai`` provider. Also the base class for ``ollama``, which
exposes an OpenAI-compatible endpoint at ``/v1``.
"""

from __future__ import annotations

from typing import Any

from openai import APIError, OpenAI
from openai.types.chat import ChatCompletion

from vision_mcp.providers.base import VisionProvider, VisionProviderError, VisionRequest


def _build_messages(request: VisionRequest) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]
    for base64_data, media_type in request.images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64_data}",
                    "detail": request.image_detail,
                },
            }
        )
    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": content},
    ]


class OpenAIProvider(VisionProvider):
    """Vision via the OpenAI SDK (and any OpenAI-compatible endpoint)."""

    def _client(self) -> OpenAI:
        kwargs: dict[str, Any] = {
            "api_key": self.api_key or "not-needed",
            "timeout": self.request_timeout,
            "max_retries": 2,
        }
        if self.api_url:
            kwargs["base_url"] = self.api_url
        return OpenAI(**kwargs)

    def generate(self, request: VisionRequest) -> str:
        try:
            completion: ChatCompletion = self._client().chat.completions.create(
                model=self.model,
                messages=_build_messages(request),
                max_tokens=request.max_tokens or self.max_output_tokens,
            )
        except APIError as exc:
            raise VisionProviderError(
                f"OpenAI-compatible API error ({exc.status_code}): {exc.message}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - normalise SDK errors
            raise VisionProviderError(f"OpenAI-compatible request failed: {exc}") from exc

        content = completion.choices[0].message.content
        if content is None:
            raise VisionProviderError("The model returned no text content.")
        return content.strip()
