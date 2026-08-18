"""Tests for the pipeline: reading sources, encoding, and model dispatch."""

import base64
import io

import httpx
import pytest
from PIL import Image

from vision_mcp import pipeline


def _png(size=(64, 48), text=True):
    img = Image.new("RGB", size, (200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _data_uri(size=(64, 48)):
    return "data:image/png;base64," + base64.b64encode(_png(size)).decode()


def test_read_data_uri():
    raw = pipeline._read(_data_uri())
    assert raw == _png()


def test_read_file_path(tmp_path):
    path = tmp_path / "pic.png"
    path.write_bytes(_png())
    assert pipeline._read(str(path)) == _png()


def test_read_url(monkeypatch):
    raw = _png()

    class FakeResp:
        content = raw

        def raise_for_status(self):
            return None

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    assert pipeline._read("https://example.com/pic.png") == raw


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        pipeline._read(str(tmp_path / "nope.png"))


def test_encode_small_image_keeps_format():
    b64, mime = pipeline._encode(_png(), max_mb=5)
    assert mime == "image/png"
    assert base64.b64decode(b64) == _png()


def test_encode_big_image_is_shrunk_to_jpeg():
    noisy = Image.effect_noise((4000, 3000), 100).convert("RGB")
    buf = io.BytesIO()
    noisy.save(buf, format="JPEG", quality=95)
    raw = buf.getvalue()

    b64, mime = pipeline._encode(raw, max_mb=0.05)
    assert mime == "image/jpeg"
    assert len(base64.b64decode(b64)) <= 0.05 * 1024 * 1024


def test_encode_garbage_raises():
    with pytest.raises(ValueError, match="image"):
        pipeline._encode(b"not an image", max_mb=5)


def test_look_dispatches_to_provider(monkeypatch):
    calls = []

    def fake_api(cfg, images, prompt):
        calls.append((cfg, images, prompt))
        return "I see a red rectangle."

    monkeypatch.setitem(pipeline.API, "ollama", fake_api)
    cfg = {"provider": "ollama", "max_image_mb": 5}
    out = pipeline.look(cfg, [_data_uri()], "What do you see?")

    assert out == "I see a red rectangle."
    assert calls[0][2] == "What do you see?"
    assert calls[0][1][0][1] == "image/png"


def test_look_wraps_provider_errors(monkeypatch):
    def bad_api(cfg, images, prompt):
        raise ConnectionError("boom")

    monkeypatch.setitem(pipeline.API, "ollama", bad_api)
    with pytest.raises(RuntimeError, match="ollama call failed: boom"):
        pipeline.look({"provider": "ollama", "max_image_mb": 5}, [_data_uri()], "hi")


def test_openai_message_uses_data_uri(monkeypatch):
    import types

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            content = types.SimpleNamespace(content="ok")
            msg = types.SimpleNamespace(message=content)
            return types.SimpleNamespace(choices=[msg])

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", lambda **kw: FakeClient())
    cfg = {"api_key": "k", "api_url": "http://x/v1", "model": "m", "timeout": 30}
    out = pipeline._openai_api(cfg, [("AAAA", "image/png")], "look")
    assert out == "ok"
    url = captured["messages"][1]["content"][1]["image_url"]["url"]
    assert url == "data:image/png;base64,AAAA"


def test_anthropic_message_uses_base64_block(monkeypatch):
    import types

    captured = {}

    class FakeContent:
        type = "text"
        text = "hi there"

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(content=[FakeContent()])

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", lambda **kw: FakeClient())
    cfg = {"api_key": "k", "api_url": "http://x", "model": "m", "timeout": 30}
    out = pipeline._anthropic_api(cfg, [("AAAA", "image/png")], "look")
    assert out == "hi there"
    block = captured["messages"][0]["content"][0]
    assert block["source"] == {"type": "base64", "media_type": "image/png", "data": "AAAA"}
