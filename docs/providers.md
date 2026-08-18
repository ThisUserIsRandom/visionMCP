# Provider setup

visionMCP supports three vision backends. Pick one with the `provider` key in
`config.json`. An OpenAI-compatible endpoint is also usable through the `openai`
provider (point `api_url` anywhere OpenAI-compatible).

## Ollama (fully local, no API key)

1. [Install Ollama](https://ollama.com/download) and start it:
   ```bash
   ollama serve
   ```
2. Pull a vision-capable model:
   ```bash
   ollama pull llama3.2-vision
   # or: qwen2.5vl:7b, llava, minicpm-v, ...
   ```
3. Configure:
   ```json
   {
     "provider": "ollama",
     "api_url": "http://localhost:11434/v1",
     "model": "llama3.2-vision"
   }
   ```
4. Verify the endpoint directly:
   ```bash
   curl http://localhost:11434/v1/models
   ```

> `api_key` is ignored by Ollama. Anything non-empty works if your MCP client
> injects one; the server substitutes a placeholder when it is empty.

### Useful Ollama vision models

| Model                  | Notes                                      |
|------------------------|--------------------------------------------|
| `llama3.2-vision`      | Default; strong general vision (11B)       |
| `qwen2.5vl`            | Excellent OCR and fine-grained detail      |
| `llava`                | Lightweight, fast                          |
| `minicpm-v`            | Document/chart heavy reading               |

## OpenAI

1. Get an API key from the [OpenAI platform](https://platform.openai.com/api-keys).
2. Configure:
   ```json
   {
     "provider": "openai",
     "api_key": "sk-...",
     "model": "gpt-4o-mini"
   }
   ```
   `api_url` defaults to `https://api.openai.com/v1`.
3. Or keep keys out of the file:
   ```bash
   export OPENAI_API_KEY=sk-...
   uv run vision-mcp
   ```

### Using any OpenAI-compatible endpoint (vLLM, LM Studio, Together, ...)

Point `api_url` at the compatible server.

```json
{
  "provider": "openai",
  "api_key": "not-needed",
  "api_url": "http://localhost:8000/v1",
  "model": "Qwen/Qwen2.5-VL-7B-Instruct"
}
```

## Anthropic

1. Get an API key from the [Anthropic console](https://console.anthropic.com/).
2. Configure:
   ```json
   {
     "provider": "anthropic",
     "api_key": "sk-ant-...",
     "model": "claude-3-5-sonnet-latest"
   }
   ```
   `api_url` defaults to `https://api.anthropic.com`.
3. Or use the env var:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   uv run vision-mcp
   ```

### Anthropic vision models

| Model                        | Notes                                    |
|------------------------------|------------------------------------------|
| `claude-3-5-sonnet-latest`   | Default; strong all-round vision + OCR   |
| `claude-3-7-sonnet-latest`   | Best reasoning, more expensive           |
| `claude-3-5-haiku-latest`    | Fast and cheap                           |

## Provider behaviour notes

- **Ollama**: uses the OpenAI-compatible endpoint; identical request shape to
  OpenAI. Models must be pulled before use.
- **OpenAI**: image URLs are sent as base64 `data:` URIs. `gpt-4o*` models
  support vision; `gpt-4` and `gpt-3.5-turbo` do not.
- **Anthropic**: images are sent as base64 content blocks. Claude vision models
  have a 5 MB per-image limit — visionMCP's auto-downscaling keeps images under
  this.
- **Errors**: provider/network failures surface as descriptive tool errors the
  calling LLM can act on.