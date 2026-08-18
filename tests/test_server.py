"""End-to-end tests against the FastMCP server using an in-process client."""

from __future__ import annotations

import base64
import io
import json

import pytest
from fastmcp import Client
from PIL import Image

from vision_mcp.config import ServerConfig
from vision_mcp.server import build_server


class FakeProvider:
    """Records requests and returns canned answers — no network."""

    def __init__(self) -> None:
        self.requests: list = []

    @property
    def provider_name(self) -> str:
        return "fake"

    def generate(self, request) -> str:
        self.requests.append(request)
        return "The image shows a red rectangle."


@pytest.fixture
def server_and_provider(monkeypatch):
    config = ServerConfig(provider="openai", api_key="sk-test", model="gpt-4o-mini")
    fake = FakeProvider()
    monkeypatch.setattr("vision_mcp.server.create_provider", lambda cfg: fake)
    server = build_server(config)
    return server, fake


def _png_data_uri() -> str:
    img = Image.new("RGB", (64, 48), (200, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


async def test_tools_are_registered(server_and_provider):
    server, _ = server_and_provider
    async with Client(server) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert {
        "describe_image",
        "ask_about_image",
        "extract_text",
        "compare_images",
        "server_status",
    } <= names


async def test_server_status_reports_config(server_and_provider):
    server, _ = server_and_provider
    async with Client(server) as client:
        result = await client.call_tool_mcp("server_status", {})
    assert result.isError is False
    text = result.content[0].text
    data = json.loads(text)
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o-mini"
    assert data["api_key_configured"] is True
    assert "api_key" not in text or data.get("api_key") is None


async def test_describe_image_reaches_provider(server_and_provider):
    server, fake = server_and_provider
    async with Client(server) as client:
        result = await client.call_tool_mcp(
            "describe_image", {"image": _png_data_uri()}
        )
    assert result.isError is False
    payload = json.loads(result.content[0].text)
    assert payload["answer"] == "The image shows a red rectangle."
    assert payload["image"]["width"] == 64
    assert payload["image"]["height"] == 48
    assert len(fake.requests) == 1
    req = fake.requests[0]
    assert len(req.images) == 1
    assert req.images[0][1] == "image/png"


async def test_ask_and_compare_route_questions(server_and_provider):
    server, fake = server_and_provider
    async with Client(server) as client:
        await client.call_tool_mcp(
            "ask_about_image", {"image": _png_data_uri(), "question": "What color?"}
        )
        await client.call_tool_mcp(
            "compare_images",
            {"image_a": _png_data_uri(), "image_b": _png_data_uri()},
        )
    assert len(fake.requests) == 2
    assert "What color?" in fake.requests[0].prompt
    assert len(fake.requests[1].images) == 2


async def test_missing_file_returns_tool_error(server_and_provider):
    server, _ = server_and_provider
    async with Client(server) as client:
        result = await client.call_tool_mcp(
            "describe_image", {"image": "/nonexistent/photo.png"}
        )
    assert result.isError is True
    assert "not found" in result.content[0].text
