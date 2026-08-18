"""End-to-end tests against the FastMCP server via an in-process client."""

import pytest
from fastmcp import Client

from vision_mcp.config import load_config
from vision_mcp.server import build_server


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr("vision_mcp.pipeline.look", fake_look)
    cfg = load_config(overrides={"provider": "openai", "api_key": "sk-test"})
    return build_server(cfg)


def fake_look(cfg, images, prompt):
    fake_look.calls.append((images, prompt))
    return f"answer for {len(images)} image(s)"


fake_look.calls = []


async def test_tools_are_registered(server):
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


async def test_server_status_reports_config(server):
    import json

    async with Client(server) as client:
        result = await client.call_tool_mcp("server_status", {})
    assert result.isError is False
    data = json.loads(result.content[0].text)
    assert data["provider"] == "openai"
    assert data["model"] == "gpt-4o-mini"
    assert data["api_key_set"] is True


async def test_describe_sends_one_image(server):
    async with Client(server) as client:
        result = await client.call_tool_mcp(
            "describe_image", {"image": "data:image/png;base64,AAAA"}
        )
    assert result.content[0].text == "answer for 1 image(s)"
    assert len(fake_look.calls[-1][0]) == 1


async def test_compare_sends_two_images(server):
    async with Client(server) as client:
        result = await client.call_tool_mcp(
            "compare_images", {"image_a": "a.png", "image_b": "b.png"}
        )
    assert result.content[0].text == "answer for 2 image(s)"


async def test_missing_file_returns_tool_error(server, monkeypatch):
    monkeypatch.setattr(
        "vision_mcp.pipeline.look",
        lambda cfg, images, prompt: (_ for _ in ()).throw(
            ValueError("File not found: /nope.png")
        ),
    )
    async with Client(server) as client:
        result = await client.call_tool_mcp(
            "describe_image", {"image": "/nope.png"}
        )
    assert result.isError is True
    assert "not found" in result.content[0].text
