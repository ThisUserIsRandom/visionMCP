# Configuration

Everything lives in `config.json` — just nine keys. Missing values fall back to
sensible defaults, so the file can be tiny.

## Precedence (highest wins)

1. CLI flags (`--provider`, `--model`, ...)
2. `VISIONMCP_*` environment variables
3. `config.json`
4. Built-in defaults (including per-provider URL and model)

## Keys

| Key          | Default (empty = per provider) | Description                                          |
|--------------|-------------------------------|------------------------------------------------------|
| `provider`   | `ollama`                      | `ollama` \| `openai` \| `anthropic`                  |
| `api_key`    | `""`                          | Falls back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`. Ignored by Ollama. |
| `api_url`    | `""`                          | Empty → provider default URL.                        |
| `model`      | `""`                          | Empty → provider default model.                      |
| `max_image_mb` | `5`                         | Images larger than this are shrunk to JPEG.          |
| `timeout`    | `120`                         | Seconds for model calls and image downloads.         |
| `transport`  | `stdio`                       | `stdio` \| `http` \| `sse` \| `streamable-http`      |
| `host`       | `0.0.0.0`                     | Bind address for http/sse.                           |
| `port`       | `8100`                        | Port for http/sse.                                   |

Provider defaults:

| Provider   | Default `api_url`           | Default `model`              |
|------------|-----------------------------|------------------------------|
| `ollama`   | `http://localhost:11434/v1` | `llama3.2-vision`            |
| `openai`   | `https://api.openai.com/v1` | `gpt-4o-mini`                |
| `anthropic`| `https://api.anthropic.com` | `claude-3-5-sonnet-latest`   |

## Environment variables

| Env var                    | Config key    |
|----------------------------|---------------|
| `VISIONMCP_PROVIDER`       | `provider`    |
| `VISIONMCP_API_KEY`        | `api_key`     |
| `VISIONMCP_API_URL`        | `api_url`     |
| `VISIONMCP_MODEL`          | `model`       |
| `VISIONMCP_TRANSPORT`      | `transport`   |
| `VISIONMCP_PORT`           | `port`        |

Plus `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` when `api_key` is empty.

## Examples

```jsonc
// local, fully private (default)
{ "provider": "ollama" }

// OpenAI
{ "provider": "openai", "api_key": "sk-...", "model": "gpt-4o-mini" }

// Anthropic, key from env
{ "provider": "anthropic" }
export ANTHROPIC_API_KEY=sk-ant-...
```

## Check the resolved config

```bash
uv run vision-mcp --show-config
```

Prints the final config (API key masked) and exits.