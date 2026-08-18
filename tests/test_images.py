"""Tests for image source resolution and encoding."""

from __future__ import annotations

import base64
import io

import httpx
import pytest
from PIL import Image

from vision_mcp.images import ImageSourceError, encode_image


def _make_image_bytes(fmt: str = "PNG", size: tuple[int, int] = (64, 48)) -> bytes:
    img = Image.new("RGB", size, (200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_data_uri_roundtrip():
    raw = _make_image_bytes("PNG")
    uri = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    img = encode_image(uri)
    assert img.media_type == "image/png"
    assert (img.width, img.height) == (64, 48)
    assert img.source_kind == "data-uri"
    assert base64.b64decode(img.base64) == raw


def test_local_file_path(tmp_path):
    path = tmp_path / "photo.png"
    path.write_bytes(_make_image_bytes("PNG"))
    img = encode_image(str(path))
    assert img.media_type == "image/png"
    assert img.source_kind == "path"


def test_url_is_downloaded(monkeypatch):
    raw = _make_image_bytes("PNG")

    class FakeResponse:
        content = raw

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse())
    img = encode_image("https://example.com/pic.png")
    assert img.media_type == "image/png"
    assert img.source_kind == "url"
    assert (img.width, img.height) == (64, 48)


def test_oversized_image_is_downscaled(tmp_path):
    noisy = Image.effect_noise((4000, 3000), 100).convert("RGB")
    buf = io.BytesIO()
    noisy.save(buf, format="JPEG", quality=95)
    raw = buf.getvalue()
    assert len(raw) > 1024 * 1024
    path = tmp_path / "big.jpg"
    path.write_bytes(raw)

    img = encode_image(str(path), max_image_mb=0.05, max_image_dimension=512)
    assert img.resized is True
    assert img.media_type == "image/jpeg"
    assert img.final_bytes <= 0.05 * 1024 * 1024
    assert max(img.width, img.height) <= 512


def test_png_kept_as_png_when_small(tmp_path):
    raw = _make_image_bytes("PNG", (200, 100))
    path = tmp_path / "small.png"
    path.write_bytes(raw)
    img = encode_image(str(path), max_image_mb=5.0)
    assert img.resized is False
    assert img.media_type == "image/png"


def test_missing_file_raises(tmp_path):
    with pytest.raises(ImageSourceError, match="not found"):
        encode_image(str(tmp_path / "missing.png"))


def test_garbage_bytes_raise():
    with pytest.raises(ImageSourceError, match="image format"):
        encode_image("data:image/png;base64," + base64.b64encode(b"not an image").decode())


def test_alpha_png_downscale_is_handled(tmp_path):
    rgba = Image.new("RGBA", (3000, 2000), (10, 20, 30, 128))
    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    path = tmp_path / "alpha.png"
    path.write_bytes(buf.getvalue())
    img = encode_image(str(path), max_image_mb=0.02, max_image_dimension=800)
    assert img.media_type == "image/jpeg"
    assert img.resized is True
