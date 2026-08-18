"""CLI: uv run vision-mcp [--config FILE] [--transport stdio|http|sse] ..."""

import argparse
import json

from . import __version__
from .config import load_config
from .server import build_server


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="vision-mcp", description="MCP server that gives an LLM eyes."
    )
    parser.add_argument("--config", default="config.json", help="config.json file")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], help="MCP transport")
    parser.add_argument("--host", help="bind address (http/sse)")
    parser.add_argument("--port", type=int, help="port (http/sse)")
    parser.add_argument("--provider", help="vision provider")
    parser.add_argument("--model", help="vision model")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--api-url", help="API base URL")
    parser.add_argument("--show-config", action="store_true", help="print config and exit")
    parser.add_argument("--version", action="version", version=f"vision-mcp {__version__}")
    args = parser.parse_args(argv)

    overrides = {
        k: v
        for k, v in {
            "provider": args.provider,
            "model": args.model,
            "api_key": args.api_key,
            "api_url": args.api_url,
            "transport": args.transport,
            "host": args.host,
            "port": args.port,
        }.items()
        if v is not None
    }

    cfg = load_config(args.config, overrides)

    if args.show_config:
        cfg["api_key"] = "***" if cfg["api_key"] else ""
        print(json.dumps(cfg, indent=2))
        return 0

    server = build_server(cfg)
    if cfg["transport"] == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport=cfg["transport"], host=cfg["host"], port=cfg["port"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
