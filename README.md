# visionMCP 👁️

**The eyes of a bigger reasoning LLM.**

`visionMCP` is a [Model Context Protocol](https://modelcontextprotocol.io/) server that
gives any MCP-capable agent real **vision**. A text-only reasoning model can delegate
anything it cannot see to this server: describe a screenshot, answer a question about a
photo, OCR a document, or compare two images — the server does the seeing and hands back
text.

It works with **all three major vision backends**, chosen at runtime from a single
`config.json`:

| Provider   | API                                                     | Example models                      |
|------------|---------------------------------------------------------|-------------------------------------|
| Ollama     | OpenAI-compatible (`http://localhost:11434/v1`)         | `llama3.2-vision`, `qwen2.5vl`, `llava` |
| OpenAI     | Chat Completions vision API                             | `gpt-4o`, `gpt-4o-mini`             |
| Anthropic  | Claude Messages vision API                              | `claude-3-5-sonnet-latest`, `claude-3-7-sonnet-latest` |

---

## Features

- 🔍 **Four vision tools** for a reasoning LLM to call:
  - `describe_image` — full natural-language description
  - `ask_about_image` — targeted Q&A about any image
  - `extract_text` — OCR / transcription
  - `compare_images` — side-by-side comparison
- 🖼️ **Every source accepted**: local file paths, `http(s)` URLs, and base64
  `data:` URIs.
- 📦 **Zero image prep**: oversized images are auto-downscaled and re-encoded as
  JPEG to fit provider payload limits.
- 🔌 **Three transports**: `stdio` (default, for local MCP clients), `http`
  (Streamable HTTP for remote hosting), or `sse` (legacy Server-Sent Events).
- ⚙️ **One `config.json`** controls provider, API key, API URL, and model.
  Environment variables and CLI flags can override anything.
- 🚀 **`uv`-managed**, installable, runnable, and hostable.

---

## Quick start

### 1. Install

Requires [uv](https://docs.astral.sh/uv/) and Python ≥ 3.10.

```bash
cd visionMCP
uv sync
```

### 2. Configure

The shipped `config.json` already works with a local Ollama. Switch providers by
editing the file:

```jsonc
// config.json
{
  "provider": "openai",                  // "ollama" | "openai" | "anthropic"
  "api_key": "sk-...",                   // or leave "" and export OPENAI_API_KEY
  "api_url": "",                         // "" = provider default
  "model": ""                            // "" = provider default
}
```

See [docs/configuration.md](docs/configuration.md) for every option, and
[docs/providers.md](docs/providers.md) for per-provider setup.

> **Security:** keep real API keys out of git — copy `config.json` to
> `config.local.json` (auto-ignored) or use environment variables. The server
> never logs your key.

### 3. Run

```bash
uv run vision-mcp                        # stdio transport (default)
uv run vision-mcp --transport http --host 0.0.0.0 --port 8100   # host remotely
uv run vision-mcp --show-config          # print resolved config (key masked)
```

## Wiring into an MCP client

### opencode (`opencode.json`)

```json
{
  "mcpServers": {
    "visionMCP": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/visionMCP", "vision-mcp"]
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "visionMCP": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/visionMCP", "vision-mcp"]
    }
  }
}
```

### Generic MCP client (stdio)

```json
{
  "mcpServers": {
    "visionMCP": {
      "command": "/path/to/visionMCP/.venv/bin/vision-mcp",
      "args": ["--config", "/path/to/visionMCP/config.json"]
    }
  }
}
```

> The server never sends image *content* to the vision API beyond what the tool
> call provides. Image bytes are kept in memory and never written to disk.

---

## Tools reference

| Tool               | Arguments                                                  | Returns                          |
|--------------------|------------------------------------------------------------|----------------------------------|
| `describe_image`   | `image` (path/URL/data-URI)                                | Full description in plain text   |
| `ask_about_image`  | `image`, `question`                                        | Focused answer                   |
| `extract_text`     | `image`                                                    | Transcribed / OCR'd text         |
| `compare_images`   | `image_a`, `image_b`, optional `question`                  | Comparison in plain text         |
| `server_status`    | —                                                          | Provider, model, transport       |

An `image` argument accepts any of:

```
/path/to/photo.png          # local file
https://example.com/x.jpg   # URL (downloaded at call time)
data:image/png;base64,iVBORw0KGgo...   # base64 data URI
```

## How it works

Everything funnels through one function in `src/vision_mcp/pipeline.py`:

```text
image (path / URL / data URI)  →  base64 + mime  →  vision model  →  text
        _read()                     _encode()         API[provider]    look()
```

The server tools are thin wrappers: `pipeline.look(cfg, [image], prompt)`.

---

## Documentation

- [Configuration reference](docs/configuration.md) — every config option, env
  var, and precedence rules
- [Provider setup](docs/providers.md) — Ollama, OpenAI, and Anthropic, step by step
- [Deployment](docs/deployment.md) — hosting over HTTP/SSE, Docker, hardening

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest
```

## License

MIT