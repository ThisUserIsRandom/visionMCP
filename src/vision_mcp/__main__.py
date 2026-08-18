"""CLI entry point for visionMCP.

``vision-mcp`` is the executable defined in ``pyproject.toml``; this module also
allows ``uv run vision-mcp`` or ``python -m vision_mcp``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from vision_mcp import __version__
from vision_mcp.config import (
    SUPPORTED_PROVIDERS,
    SUPPORTED_TRANSPORTS,
    ConfigError,
    load_config,
)
from vision_mcp.server import build_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision-mcp",
        description=(
            "MCP server that gives vision (image analysis) to a larger reasoning "
            "LLM, backed by Ollama, OpenAI, or Anthropic."
        ),
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to config.json (default: VISIONMCP_CONFIG or ./config.json).",
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        help="Override the configured vision provider.",
    )
    parser.add_argument(
        "--model",
        help="Override the configured model name.",
    )
    parser.add_argument(
        "--api-key",
        help="Override the configured API key (or the provider's env var).",
    )
    parser.add_argument(
        "--api-url",
        help="Override the configured API base URL.",
    )
    parser.add_argument(
        "--transport",
        choices=SUPPORTED_TRANSPORTS,
        help="Override the configured transport (default from config).",
    )
    parser.add_argument(
        "--host",
        help="Bind address for http/sse/streamable-http transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for http/sse/streamable-http transports.",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print the resolved configuration (API key masked) and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"vision-mcp {__version__}",
    )
    return parser


def _overrides_from_args(args: argparse.Namespace) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    mapping = {
        "provider": "provider",
        "model": "model",
        "api_key": "api_key",
        "api_url": "api_url",
        "transport": "transport",
        "host": "host",
        "port": "port",
    }
    for cli_attr, cfg_key in mapping.items():
        value = getattr(args, cli_attr, None)
        if value is not None:
            overrides[cfg_key] = value
    return overrides


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(
            path=args.config,
            overrides=_overrides_from_args(args),
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        print(
            "Run 'vision-mcp --show-config' after fixing config.json, or check "
            "docs/configuration.md.",
            file=sys.stderr,
        )
        return 2

    if args.show_config:
        print(json.dumps(config.redacted_dict(), indent=2, ensure_ascii=False))
        return 0

    server = build_server(config)
    transport = config.transport

    if transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport=transport, host=config.host, port=config.port)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
