"""The whole pipeline in one place: image in, text out.

    look(cfg, images, prompt)
      1. reads each image   (file path, URL, or data URI)
      2. shrinks any that are too big for the model API
      3. asks the configured vision model (Ollama, OpenAI, or Anthropic)
      4. returns the model's text answer
"""

import base64
import io
import os

import httpx
from PIL import Image

SYSTEM = (
    "You are the eyes of a larger reasoning LLM. Look at the image(s) and "
    "answer the user's request briefly and accurately."
)


# --- 1. read the image as bytes -----------------------------------------

def _read(source):
    if source.startswith("data:"):
        try:
            return base64.b64decode(source.split(",", 1)[1])
        except Exception:
            raise ValueError("Invalid data URI") from None
    if source.startswith(("http://", "https://")):
        resp = httpx.get(source, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    if not os.path.exists(source):
        raise ValueError(f"File not found: {source}")
    with open(source, "rb") as fh:
        return fh.read()


# --- 2. turn bytes into (base64, mime type), shrinking when too big -----

def _mime(img):
    return {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "WEBP": "image/webp",
        "GIF": "image/gif",
    }.get(img.format, "image/jpeg")


def _encode(raw, max_mb):
    try:
        img = Image.open(io.BytesIO(raw))
    except Exception:
        raise ValueError("Not a valid image file") from None

    limit = int(max_mb * 1024 * 1024)
    if len(raw) <= limit:
        return base64.b64encode(raw).decode(), _mime(img)

    # too big: re-encode as a smaller JPEG, shrinking until it fits
    if img.mode != "RGB":
        img = img.convert("RGB")
    edge = 1568
    while True:
        img.thumbnail((edge, edge))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        data = buf.getvalue()
        if len(data) <= limit or img.width < 64:
            return base64.b64encode(data).decode(), "image/jpeg"
        edge = int(edge * 0.8)


# --- 3. ask the model ---------------------------------------------------

def _openai_api(cfg, images, prompt):
    from openai import OpenAI

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["api_url"], timeout=cfg["timeout"])
    content = [{"type": "text", "text": prompt}] + [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        for b64, mime in images
    ]
    out = client.chat.completions.create(
        model=cfg["model"],
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": content},
        ],
    )
    return out.choices[0].message.content.strip()


def _ollama_api(cfg, images, prompt):
    return _openai_api({**cfg, "api_key": cfg["api_key"] or "ollama"}, images, prompt)


def _anthropic_api(cfg, images, prompt):
    from anthropic import Anthropic

    client = Anthropic(api_key=cfg["api_key"], base_url=cfg["api_url"], timeout=cfg["timeout"])
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}}
        for b64, mime in images
    ] + [{"type": "text", "text": prompt}]
    out = client.messages.create(
        model=cfg["model"],
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in out.content if b.type == "text").strip()


API = {"ollama": _ollama_api, "openai": _openai_api, "anthropic": _anthropic_api}


def look(cfg, images, prompt):
    """Run the whole pipeline: image sources -> model's text answer."""
    encoded = [_encode(_read(src), cfg["max_image_mb"]) for src in images]
    try:
        return API[cfg["provider"]](cfg, encoded, prompt)
    except Exception as exc:
        raise RuntimeError(f"{cfg['provider']} call failed: {exc}") from exc
