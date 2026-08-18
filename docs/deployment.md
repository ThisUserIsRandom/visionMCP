# Deployment

visionMCP runs on `stdio` out of the box for local MCP clients, and can be
hosted as an HTTP/SSE server for remote agents. This page covers running,
hosting, hardening, and packaging.

## Transports

| Transport         | Best for                                   |
|-------------------|---------------------------------------------|
| `stdio` (default) | Local MCP clients that spawn a subprocess   |
| `http`            | Remote hosting; Streamable HTTP at `/mcp`   |
| `sse`             | Legacy Server-Sent-Events clients           |

> `transport="http"` serves the modern Streamable HTTP endpoint (POST + SSE
> responses) at `/mcp`. Legacy SSE-only clients should use `transport="sse"`,
> which serves the SSE endpoint (default `/sse`).

## Running

```bash
# stdio (default)
uv run vision-mcp

# explicit transport
uv run vision-mcp --transport stdio

# host over HTTP (Streamable HTTP endpoint at /mcp)
uv run vision-mcp --transport http --host 0.0.0.0 --port 8100

# host with legacy SSE transport (endpoint at /sse)
uv run vision-mcp --transport sse --host 0.0.0.0 --port 8100

# host with a custom config file
uv run vision-mcp --transport http --config /etc/visionMCP/config.json
```

### Service manager (systemd)

```ini
# /etc/systemd/system/visionmcp.service
[Unit]
Description=visionMCP server
After=network.target

[Service]
User=visionmcp
WorkingDirectory=/opt/visionMCP
Environment=VISIONMCP_CONFIG=/etc/visionMCP/config.json
ExecStart=/opt/visionMCP/.venv/bin/vision-mcp --transport http --host 127.0.0.1 --port 8100
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Docker

A small, layered `Dockerfile` (Python 3.12 slim + uv):

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY config.json ./config.json

EXPOSE 8100
ENTRYPOINT ["uv", "run", "--no-sync", "vision-mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8100"]
```

```bash
docker build -t visionmcp .
docker run --rm -p 8100:8100 \
  -v "$PWD/config.json:/app/config.json:ro" \
  visionmcp
```

## Hardening

- **Never commit real API keys.** Use `config.local.json` (git-ignored) or env
  vars. Keys are masked in `--show-config` and never logged.
- **Bound the HTTP listener** to `127.0.0.1` unless you intend LAN/WAN access;
  put a reverse proxy (Caddy/nginx) with TLS in front for internet exposure.
- **Restrict image sources.** Tools accept arbitrary file paths and URLs. In a
  multi-tenant deployment, front the server with your own authorization layer
  and, if needed, an allowlist of paths/hosts.
- **Rate limits & size caps** are configurable (`max_image_mb`, `timeout`).
  Downscaling keeps payloads bounded even for pathological inputs.
- **Secrets via env** keeps the config file free of keys — recommended for CI/CD.

## Packaging

```bash
uv build                # wheel + sdist into dist/
uv publish              # upload to PyPI (after configuring credentials)
```

Install anywhere with pip/uv once published:

```bash
pip install vision-mcp
vision-mcp --config /etc/visionMCP/config.json
```

## Observability

- `vision-mcp --show-config` prints the resolved configuration (key masked).
- `server_status` tool reports provider/model/transport/limits at runtime.
- Provider and model errors are returned as descriptive tool errors the calling
  agent can handle.