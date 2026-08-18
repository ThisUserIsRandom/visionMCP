# Configuration

All server behaviour is driven by a single `config.json` plus environment
variable and CLI overrides. This page documents every option.

## Precedence

Values are resolved **highest wins**:

1. **CLI / programmatic overrides** (`--provider`, `--model`, ...)
2. **Environment variables** prefixed `VISIONMCP_`
3. **`config.json`** (or the file named by `VISIONMCP_CONFIG`)
4. **Built-in defaults**, including per-provider default URL and model

## Config file location

By default the server looks for `config.json` in the current working directory.

| Method                          | Command / example                                            |
|---------------------------------|--------------------------------------------------------------|
| Default                         | `uv run vision-mcp` (reads `./config.json`)                  |
| Explicit file                   | `uv run vision-mcp --config /etc/visionMCP/config.json`      |
| Environment variable            | `VISIONMCP_CONFIG=/etc/visionMCP/config.json uv run vision-mcp` |

A JSON Schema (`config.schema.json`) is bundled for editor autocomplete and
validation:

```bash
uv run python -c "import json,jsonschema; jsonschema.validate(json.load(open('config.json')), json.load(open('config.schema.json')))"
```

## Options

| Key                     | Type    | Default (per provider)                         | Description                                                                 |
|-------------------------|---------|------------------------------------------------|-----------------------------------------------------------------------------|
| `provider`              | string  | `ollama`                                       | `ollama`, `openai`, or `anthropic`                                          |
| `api_key`               | string  | `""`                                           | API key. Empty → falls back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`. Ignored for Ollama. |
| `api_url`               | string  | see table below                                | API base URL. Ollama uses its OpenAI-compatible endpoint.                   |
| `model`                 | string  | see table below                                | Vision model name.                                                          |
| `default_prompt`        | string  | built-in "eyes of a reasoning LLM" system prompt | System prompt sent with every request.                                      |
| `image_detail`          | string  | `auto`                                         | Resolution hint for OpenAI/Ollama-compatible APIs: `auto`, `low`, `high`.   |
| `max_image_mb`          | number  | `5.0`                                          | Payload ceiling in MB. Larger images are auto-downscaled to JPEG.           |
| `max_image_dimension`   | integer | `1568`                                         | Longest edge in px after resizing.                                          |
| `jpeg_quality`          | integer | `82`                                           | JPEG quality (30–95) used when re-encoding oversized images.                |
| `request_timeout_seconds` | number | `120.0`                                      | Timeout for provider calls and image URL downloads.                         |
| `max_output_tokens`     | integer | `2048`                                         | Max tokens the model may generate per call.                                 |
| `server_name`           | string  | `visionMCP`                                    | Name advertised by the MCP server.                                          |
| `transport`             | string  | `stdio`                                        | `stdio`, `http` (Streamable HTTP), `sse`. |
| `host`                  | string  | `0.0.0.0`                                      | Bind address for HTTP transports.                                           |
| `port`                  | integer | `8100`                                         | Port for HTTP transports.                                                   |

### Default API URLs and models

| Provider   | Default `api_url`             | Default `model`                  |
|------------|-------------------------------|----------------------------------|
| `ollama`   | `http://localhost:11434/v1`   | `llama3.2-vision`                |
| `openai`   | `https://api.openai.com/v1`   | `gpt-4o-mini`                    |
| `anthropic`| `https://api.anthropic.com`   | `claude-3-5-sonnet-latest`       |

## Environment variables

Every option can be set with an env var; env vars win over `config.json`.

| Env var                        | Config key              |
|--------------------------------|-------------------------|
| `VISIONMCP_CONFIG`             | config file path (not a config key) |
| `VISIONMCP_PROVIDER`           | `provider`              |
| `VISIONMCP_API_KEY`            | `api_key`               |
| `VISIONMCP_API_URL`            | `api_url`               |
| `VISIONMCP_MODEL`              | `model`                 |
| `VISIONMCP_TRANSPORT`          | `transport`             |
| `VISIONMCP_HOST`               | `host`                  |
| `VISIONMCP_PORT`               | `port`                  |
| `VISIONMCP_SERVER_NAME`        | `server_name`           |
| `VISIONMCP_TIMEOUT`            | `request_timeout_seconds` |
| `VISIONMCP_MAX_IMAGE_MB`       | `max_image_mb`          |
| `VISIONMCP_MAX_IMAGE_DIMENSION`| `max_image_dimension`   |
| `VISIONMCP_JPEG_QUALITY`       | `jpeg_quality`          |
| `VISIONMCP_MAX_OUTPUT_TOKENS`  | `max_output_tokens`     |
| `VISIONMCP_IMAGE_DETAIL`       | `image_detail`          |
| `VISIONMCP_DEFAULT_PROMPT`     | `default_prompt`        |

Provider-specific key env vars also work directly: `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`.

## Examples

**Ollama (fully local):**

```json
{
  "provider": "ollama",
  "api_key": "",
  "api_url": "http://localhost:11434/v1",
  "model": "llama3.2-vision"
}
```

**OpenAI:**

```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}
```

**Anthropic using an env var instead of a file key:**

```json
{
  "provider": "anthropic",
  "api_key": "",
  "model": "claude-3-5-sonnet-latest"
}
```

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run vision-mcp
```

## Checking the resolved configuration

```bash
uv run vision-mcp --show-config
```

Prints the fully resolved config (API key masked) and exits — useful for
debugging which defaults were applied.