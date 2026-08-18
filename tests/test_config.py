"""Tests for config loading: defaults, file, env vars, CLI overrides."""

import json

import pytest

from vision_mcp.config import PROVIDERS, load_config


def test_defaults_when_no_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg["provider"] == "ollama"
    assert cfg["api_url"] == PROVIDERS["ollama"]["api_url"]
    assert cfg["model"] == PROVIDERS["ollama"]["model"]
    assert cfg["transport"] == "stdio"
    assert cfg["port"] == 8100


def test_config_file_values_are_loaded(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(
        json.dumps({"provider": "openai", "api_key": "sk-test", "model": "gpt-4o"})
    )
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg["model"] == "gpt-4o"
    assert cfg["api_url"] == PROVIDERS["openai"]["api_url"]


def test_cli_overrides_beat_config_file(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(
        json.dumps({"provider": "openai", "api_key": "sk-file", "model": "gpt-4o"})
    )
    monkeypatch.chdir(tmp_path)
    cfg = load_config(overrides={"model": "gpt-4.1"})
    assert cfg["model"] == "gpt-4.1"


def test_env_overrides_config_file(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(json.dumps({"model": "gpt-4o"}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VISIONMCP_MODEL", "gpt-4o-mini")
    cfg = load_config()
    assert cfg["model"] == "gpt-4o-mini"


def test_provider_api_key_env_fallback(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(json.dumps({"provider": "anthropic"}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    cfg = load_config()
    assert cfg["api_key"] == "sk-ant-env"


def test_openai_without_key_raises(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text(json.dumps({"provider": "openai"}))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="api_key"):
        load_config()


def test_invalid_provider_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="provider"):
        load_config(overrides={"provider": "gemini"})


def test_invalid_transport_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="transport"):
        load_config(overrides={"transport": "carrier-pigeon"})
