"""Vision provider interface shared by all backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class VisionProviderError(RuntimeError):
    """Raised when a vision provider fails to produce a response."""


@dataclass(slots=True)
class VisionRequest:
    """A single request to a vision provider."""

    images: list[tuple[str, str]] = field(default_factory=list)  # [(base64, media_type)]
    prompt: str = ""
    system_prompt: str = ""
    max_tokens: int = 2048
    timeout: float = 120.0
    image_detail: str = "auto"  # used by OpenAI-compatible providers only


class VisionProvider(ABC):
    """Common interface for vision backends (Ollama, OpenAI, Anthropic)."""

    def __init__(
        self,
        *,
        api_key: str,
        api_url: str,
        model: str,
        request_timeout: float = 120.0,
        max_output_tokens: int = 2048,
        image_detail: str = "auto",
    ) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.request_timeout = request_timeout
        self.max_output_tokens = max_output_tokens
        self.image_detail = image_detail

    @property
    def provider_name(self) -> str:
        return type(self).__name__.replace("Provider", "").lower()

    @abstractmethod
    def generate(self, request: VisionRequest) -> str:
        """Send a vision request and return the model's text answer."""
