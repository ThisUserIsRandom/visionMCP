"""Image source resolution and encoding.

Tools accept an image in one of three forms:

* a local file path (``/path/to/photo.png``)
* an ``http(s)`` URL (``https://example.com/photo.jpg``)
* a base64 data URI (``data:image/png;base64,iVBORw0KGgo...``)

Every source is normalised to base64 + a MIME type that the vision providers
accept. Large images are automatically downscaled and re-encoded as JPEG so
they fit inside the provider's payload limits.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # do not error on huge images; we downscale anyway

_MIME_BY_FORMAT: dict[str, str] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
}

_MAGIC_MIME: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),
]


class ImageSourceError(ValueError):
    """Raised when an image source cannot be read, decoded, or encoded."""


@dataclass(slots=True)
class EncodedImage:
    """A normalised, provider-ready image."""

    base64: str
    media_type: str
    original_bytes: int
    final_bytes: int
    width: int
    height: int
    resized: bool
    source_kind: str  # "path" | "url" | "data-uri"


def _is_data_uri(source: str) -> bool:
    return source.startswith("data:")


def _read_data_uri(source: str) -> bytes:
    try:
        header, _, payload = source.partition(",")
        if "base64" not in header:
            raise ImageSourceError("Only base64 data URIs are supported.")
        return base64.b64decode(payload)
    except Exception as exc:  # noqa: BLE001 - normalise to our own error type
        raise ImageSourceError(f"Could not decode data URI: {exc}") from exc


def _read_url(source: str, timeout: float = 30.0) -> bytes:
    try:
        resp = httpx.get(source, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise ImageSourceError(f"Could not fetch {source}: {exc}") from exc
    if not resp.content:
        raise ImageSourceError(f"Empty response body from {source}.")
    return resp.content


def _read_path(source: str) -> bytes:
    path = Path(source)
    if not path.is_file():
        raise ImageSourceError(f"File not found: {path}")
    return path.read_bytes()


def _sniff_mime(raw: bytes) -> str:
    for magic, mime in _MAGIC_MIME:
        if raw.startswith(magic):
            return mime
    try:
        with Image.open(io.BytesIO(raw)) as im:
            mime = _MIME_BY_FORMAT.get(im.format or "")
            if mime:
                return mime
    except Exception:  # noqa: BLE001
        pass
    raise ImageSourceError(
        "Could not determine the image format. Pass a PNG/JPEG/WEBP/GIF/BMP/TIFF "
        "image from a file path, URL, or data URI."
    )


def _shrink(raw: bytes, max_bytes: int, max_dimension: int, quality: int) -> tuple[bytes, bool]:
    """Downscale/re-encode until the payload fits within ``max_bytes``."""
    img = Image.open(io.BytesIO(raw))
    scale = max_dimension / max(img.size)
    if scale < 1:
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS
        )
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= max_bytes or img.width <= 48 or quality <= 30:
            break
        img.thumbnail((int(img.width * 0.8), int(img.height * 0.8)))
        quality = max(30, quality - 10)
    return data, True


def encode_image(
    source: str,
    *,
    max_image_mb: float = 5.0,
    max_image_dimension: int = 1568,
    jpeg_quality: int = 82,
    url_timeout: float = 30.0,
) -> EncodedImage:
    """Read ``source`` and normalise it into base64 + MIME type.

    Args:
        source: A file path, http(s) URL, or base64 data URI.
        max_image_mb: Hard payload ceiling; images above this are re-encoded.
        max_image_dimension: Longest edge allowed after automatic resizing.
        jpeg_quality: JPEG quality (1-100) used when re-encoding large images.
        url_timeout: Seconds to wait when downloading a URL.

    Returns:
        An :class:`EncodedImage` ready to send to a vision provider.
    """
    if _is_data_uri(source):
        raw = _read_data_uri(source)
        source_kind = "data-uri"
    elif source.startswith(("http://", "https://")):
        raw = _read_url(source, timeout=url_timeout)
        source_kind = "url"
    else:
        raw = _read_path(source)
        source_kind = "path"

    original_bytes = len(raw)
    media_type = _sniff_mime(raw)
    resized = False

    if original_bytes > int(max_image_mb * 1024 * 1024):
        limit = int(max_image_mb * 1024 * 1024)
        raw, resized = _shrink(raw, limit, max_image_dimension, jpeg_quality)
        media_type = "image/jpeg"

    with Image.open(io.BytesIO(raw)) as im:
        width, height = im.size

    return EncodedImage(
        base64=base64.b64encode(raw).decode("ascii"),
        media_type=media_type,
        original_bytes=original_bytes,
        final_bytes=len(raw),
        width=width,
        height=height,
        resized=resized,
        source_kind=source_kind,
    )


def image_data_uri(img: EncodedImage) -> str:
    """Reconstruct a ``data:`` URI from an encoded image (OpenAI-compatible style)."""
    return f"data:{img.media_type};base64,{img.base64}"


__all__ = [
    "EncodedImage",
    "ImageSourceError",
    "encode_image",
    "image_data_uri",
]
