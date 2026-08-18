"""Tests for configuration loading, precedence, and validation."""

from __future__ import annotations

import json

import pytest

from vision_mcp.config import (
    PROVIDER_DEFAULTS,
    ConfigError,
    ServerConfig,
    load_config,
)


def _write_config(tmp_path, data: dict) -> None:
    (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")


def test_pure_defaults_when_no_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg.provider == "ollama"
    assert cfg.api_url == PROVIDER_DEFAULTS["ollama"]["api_url"]
    assert cfg.model == PROVIDER_DEFAULTS["ollama"]["model"]
    assert cfg.transport == "stdio"
    assert cfg.port == 8100


def test_config_file_values_are_loaded(tmp_path, monkeypatch):
    _write_config(
        tmp_path,
        {
            "provider": "openai",
            "api_key": "sk-test",
            "model": "gpt-4o",
            "max_image_mb": 2.5,
        },
    )
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg.provider == "openai"
    assert cfg.api_key == "sk-test"
    assert cfg.model == "gpt-4o"
    assert cfg.max_image_mb == 2.5
    assert cfg.effective_api_key() == "sk-test"


def test_provider_defaults_fill_missing_fields(tmp_path, monkeypatch):
    _write_config(tmp_path, {"provider": "anthropic", "api_key": "sk-ant-test"})
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg.model == PROVIDER_DEFAULTS["anthropic"]["model"]
    assert cfg.api_url == PROVIDER_DEFAULTS["anthropic"]["api_url"]


def test_environment_overrides_config_file(tmp_path, monkeypatch):
    _write_config(
        tmp_path,
        {"provider": "openai", "api_key": "from-file", "model": "gpt-4o"},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VISIONMCP_PROVIDER", "anthropic")
    monkeypatch.setenv("VISIONMCP_MODEL", "claude-3-7-sonnet-latest")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    cfg = load_config()
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-3-7-sonnet-latest"
    assert cfg.api_key == "from-file"


def test_cli_overrides_beat_environment(tmp_path, monkeypatch):
    _write_config(tmp_path, {"provider": "openai", "api_key": "sk-file"})
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VISIONMCP_MODEL", "gpt-4o-mini")
    cfg = load_config(overrides={"model": "gpt-4.1"})
    assert cfg.model == "gpt-4.1"


def test_missing_api_key_fails_validation(tmp_path, monkeypatch):
    _write_config(tmp_path, {"provider": "openai", "api_key": ""})
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="API key"):
        load_config()


def test_provider_env_key_is_found(tmp_path, monkeypatch):
    _write_config(tmp_path, {"provider": "openai", "api_key": ""})
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    cfg = load_config()
    assert cfg.effective_api_key() == "sk-env"


def test_invalid_provider_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="Unsupported provider"):
        load_config(overrides={"provider": "gemini"})


def test_invalid_transport_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="Unsupported transport"):
        load_config(overrides={"transport": "carrier-pigeon"})


def test_missing_explicit_config_path_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(path=str(tmp_path / "nope.json"))


def test_bad_json_raises(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text("{not json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="Invalid JSON"):
        load_config()


def test_redacted_dict_masks_key():
    cfg = ServerConfig(provider="openai", api_key="sk-super-secret")
    out = cfg.redacted_dict()
    assert out["api_key"] == "***"
    assert "sk-super-secret" not in json.dumps(out)


def test_public_dict_excludes_key():
    cfg = ServerConfig(provider="anthropic", api_key="sk-ant-secret")
    out = cfg.public_dict()
    assert "api_key" not in out
    assert out["api_key_configured"] is True
