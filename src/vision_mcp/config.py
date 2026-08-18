"""Config: just a dict. Defaults < config.json < VISIONMCP_* env vars < CLI overrides."""

import json
import os

PROVIDERS = {
    "ollama": {"api_url": "http://localhost:11434/v1", "model": "llama3.2-vision"},
    "openai": {"api_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "anthropic": {"api_url": "https://api.anthropic.com", "model": "claude-3-5-sonnet-latest"},
}

DEFAULTS = {
    "provider": "ollama",
    "api_key": "",
    "api_url": "",
    "model": "",
    "max_image_mb": 5,
    "timeout": 120,
    "transport": "stdio",
    "host": "0.0.0.0",
    "port": 8100,
}

# config key -> env var
ENV = {
    "provider": "VISIONMCP_PROVIDER",
    "api_key": "VISIONMCP_API_KEY",
    "api_url": "VISIONMCP_API_URL",
    "model": "VISIONMCP_MODEL",
    "transport": "VISIONMCP_TRANSPORT",
    "port": "VISIONMCP_PORT",
}

# provider -> well-known API key env var (fallback when api_key is empty)
KEY_ENV = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def load_config(path="config.json", overrides=None):
    """Resolve the config dict. Raises ValueError on bad input."""
    cfg = dict(DEFAULTS)

    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    for key, env in ENV.items():
        if env in os.environ:
            cfg[key] = os.environ[env]
    if overrides:
        cfg.update(overrides)

    if cfg["provider"] not in PROVIDERS:
        raise ValueError(f"provider must be one of: {', '.join(PROVIDERS)}")
    if not cfg["api_key"]:
        cfg["api_key"] = os.environ.get(KEY_ENV.get(cfg["provider"], ""), "")
    if cfg["provider"] in ("openai", "anthropic") and not cfg["api_key"]:
        env = KEY_ENV[cfg["provider"]]
        raise ValueError(f"{cfg['provider']} needs an api_key (config.json or {env})")
    if not cfg["api_url"]:
        cfg["api_url"] = PROVIDERS[cfg["provider"]]["api_url"]
    if not cfg["model"]:
        cfg["model"] = PROVIDERS[cfg["provider"]]["model"]
    if cfg["transport"] not in ("stdio", "http", "sse", "streamable-http"):
        raise ValueError("transport must be stdio, http, sse, or streamable-http")

    return cfg
