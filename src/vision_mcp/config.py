"""Configuration loading for visionMCP.

Resolution precedence (highest wins):

1. CLI / programmatic overrides (``overrides`` dict)
2. Environment variables prefixed with ``VISIONMCP_``
3. ``config.json`` (or the file pointed to by ``VISIONMCP_CONFIG``)
4. Built-in defaults (including provider-specific defaults)
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

CONFIG_PATH_ENV = "VISIONMCP_CONFIG"
ENV_PREFIX = "VISIONMCP_"
DEFAULT_CONFIG_FILENAME = "config.json"

SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic")
SUPPORTED_TRANSPORTS = ("stdio", "http", "sse", "streamable-http")

DEFAULT_SYSTEM_PROMPT = (
    "You are the vision subsystem (the 'eyes') of a larger reasoning LLM. "
    "Study the image(s) provided and answer the user's request accurately, "
    "concisely, and in the language of the request."
)

# Provider-specific defaults (api_url + a sensible default vision model).
PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "ollama": {
        "api_url": "http://localhost:11434/v1",
        "model": "llama3.2-vision",
    },
    "openai": {
        "api_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "api_url": "https://api.anthropic.com",
        "model": "claude-3-5-sonnet-latest",
    },
}

# Providers that require an API key before they will work at all.
KEY_REQUIRED_PROVIDERS = ("openai", "anthropic")


class ConfigError(ValueError):
    """Raised when the configuration is invalid or missing required values."""


@dataclass(slots=True)
class ServerConfig:
    """Resolved server configuration. Mutate fields then call :meth:`validate`."""

    provider: str = "ollama"
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    default_prompt: str = DEFAULT_SYSTEM_PROMPT
    image_detail: str = "auto"  # OpenAI-compatible detail level: auto | low | high
    max_image_mb: float = 5.0
    max_image_dimension: int = 1568
    jpeg_quality: int = 82
    request_timeout_seconds: float = 120.0
    max_output_tokens: int = 2048
    server_name: str = "visionMCP"
    transport: str = "stdio"  # stdio | http | sse | streamable-http
    host: str = "0.0.0.0"
    port: int = 8100
    config_path: str = ""

    # -- helpers ---------------------------------------------------------

    def effective_api_key(self) -> str:
        """Return the API key, falling back to the provider's well-known env var."""
        if self.api_key:
            return self.api_key
        env_name = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(
            self.provider
        )
        if env_name:
            return os.environ.get(env_name, "")
        return ""

    def validate(self) -> ServerConfig:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ConfigError(
                f"Unsupported provider {self.provider!r}. "
                f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}."
            )
        if self.transport not in SUPPORTED_TRANSPORTS:
            raise ConfigError(
                f"Unsupported transport {self.transport!r}. "
                f"Choose one of: {', '.join(SUPPORTED_TRANSPORTS)}."
            )
        if self.image_detail not in ("auto", "low", "high"):
            raise ConfigError(
                f"image_detail must be 'auto', 'low' or 'high', got {self.image_detail!r}."
            )
        if self.port < 1 or self.port > 65535:
            raise ConfigError(f"port must be 1-65535, got {self.port}.")
        if not self.model:
            raise ConfigError("No model configured. Set 'model' in config.json.")
        if self.provider in KEY_REQUIRED_PROVIDERS and not self.effective_api_key():
            raise ConfigError(
                f"Provider {self.provider!r} requires an API key. "
                "Set 'api_key' in config.json, "
                f"export the {self.provider.upper()}_API_KEY environment variable, "
                "or set VISIONMCP_API_KEY."
            )
        return self

    def public_dict(self) -> dict[str, Any]:
        """Serializable view of the config without secrets."""
        return {
            "provider": self.provider,
            "api_url": self.api_url,
            "model": self.model,
            "api_key_configured": bool(self.effective_api_key()),
            "image_detail": self.image_detail,
            "max_image_mb": self.max_image_mb,
            "max_image_dimension": self.max_image_dimension,
            "request_timeout_seconds": self.request_timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
            "server_name": self.server_name,
            "transport": self.transport,
            "host": self.host,
            "port": self.port,
            "config_path": self.config_path,
        }

    def redacted_dict(self) -> dict[str, Any]:
        """Full serializable view; the API key is masked."""
        data = self.public_dict()
        data["api_key"] = "***" if self.api_key else ""
        return data


# ---------------------------------------------------------------------------
# field name -> (env var name, parser)
# ---------------------------------------------------------------------------

_CASTERS: dict[str, Callable[[str], Any]] = {
    "provider": str,
    "api_key": str,
    "api_url": str,
    "model": str,
    "default_prompt": str,
    "image_detail": str,
    "max_image_mb": float,
    "max_image_dimension": int,
    "jpeg_quality": int,
    "request_timeout_seconds": float,
    "max_output_tokens": int,
    "server_name": str,
    "transport": str,
    "host": str,
    "port": int,
}

_FIELD_ENV: dict[str, str] = {
    "provider": "VISIONMCP_PROVIDER",
    "api_key": "VISIONMCP_API_KEY",
    "api_url": "VISIONMCP_API_URL",
    "model": "VISIONMCP_MODEL",
    "transport": "VISIONMCP_TRANSPORT",
    "host": "VISIONMCP_HOST",
    "port": "VISIONMCP_PORT",
    "server_name": "VISIONMCP_SERVER_NAME",
    "request_timeout_seconds": "VISIONMCP_TIMEOUT",
    "max_image_mb": "VISIONMCP_MAX_IMAGE_MB",
    "max_image_dimension": "VISIONMCP_MAX_IMAGE_DIMENSION",
    "jpeg_quality": "VISIONMCP_JPEG_QUALITY",
    "max_output_tokens": "VISIONMCP_MAX_OUTPUT_TOKENS",
    "image_detail": "VISIONMCP_IMAGE_DETAIL",
    "default_prompt": "VISIONMCP_DEFAULT_PROMPT",
}

# Config-file keys that are not direct ServerConfig fields.
_NON_FIELD_KEYS = ("api_key_env",)


def _default_config_path() -> str:
    return os.environ.get(CONFIG_PATH_ENV, DEFAULT_CONFIG_FILENAME)


def _load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {p}") from None
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {p} must contain a JSON object at the top level.")
    return data


def _apply_mapping(
    cfg: ServerConfig,
    data: dict[str, Any],
    *,
    source: str,
) -> None:
    for key, value in data.items():
        if key in _NON_FIELD_KEYS or not hasattr(cfg, key):
            continue
        if value is None:
            continue
        caster = _CASTERS.get(key, str)
        try:
            setattr(cfg, key, caster(value))
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"Invalid value for {key!r} ({source}): {value!r} -> {exc}"
            ) from exc


def _apply_env(cfg: ServerConfig) -> None:
    for field_name, env_name in _FIELD_ENV.items():
        if env_name in os.environ:
            setattr(cfg, field_name, _CASTERS[field_name](os.environ[env_name]))
    api_key_env = os.environ.get("VISIONMCP_API_KEY")
    if api_key_env:
        cfg.api_key = api_key_env


def load_config(
    path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
    *,
    validate: bool = True,
) -> ServerConfig:
    """Load configuration from defaults, config file, env, and overrides.

    Args:
        path: Explicit path to a config file. When omitted, ``VISIONMCP_CONFIG``
            or ``config.json`` in the current directory is used (if present).
        overrides: Programmatic overrides (e.g. CLI flags). Highest precedence.
        validate: Whether to run :meth:`ServerConfig.validate` before returning.

    Raises:
        ConfigError: if the config is invalid.
    """
    cfg = ServerConfig()

    # 1) provider-specific defaults: pick up base api_url/model for the provider.
    #    The provider itself may be overridden later; we re-apply defaults last
    #    so a changed provider always gets its own defaults unless overridden.
    def _apply_provider_defaults(target: ServerConfig) -> None:
        provider = target.provider
        if provider in PROVIDER_DEFAULTS:
            if not target.api_url:
                target.api_url = PROVIDER_DEFAULTS[provider]["api_url"]
            if not target.model:
                target.model = PROVIDER_DEFAULTS[provider]["model"]

    # 2) config file (optional unless an explicit path was requested)
    resolved_path = path or _default_config_path()
    path_missing = not Path(resolved_path).is_file()
    if path is not None and path_missing:
        raise ConfigError(f"Config file not found: {path}")
    if not path_missing:
        file_data = _load_json(resolved_path)
        _apply_mapping(cfg, file_data, source=f"config file {resolved_path}")
        cfg.config_path = str(Path(resolved_path).resolve())
    else:
        cfg.config_path = ""

    # 3) environment variables
    _apply_env(cfg)

    # 4) explicit overrides
    if overrides:
        _apply_mapping(cfg, overrides, source="overrides")

    # 5) re-apply provider defaults last so provider switching behaves
    _apply_provider_defaults(cfg)

    if validate:
        cfg.validate()
    return cfg


def provider_specific_env_names() -> dict[str, str]:
    """Map of provider -> conventional API key environment variable name."""
    return {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def field_env_map() -> dict[str, str]:
    """All supported ``VISIONMCP_*`` environment variables mapped to config keys."""
    return dict(_FIELD_ENV)


def all_field_names() -> list[str]:
    return [f.name for f in fields(ServerConfig)]
