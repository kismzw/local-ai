from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("config_check", ROOT / "scripts/config-check.py")
config_check = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(config_check)


def valid_values(tmp_path: Path) -> dict[str, str]:
    values = {
        "LLAMA_IMAGE": "./images/llama.sif", "SEARXNG_IMAGE": "./images/searx.sif", "DOCLING_IMAGE": "./images/docling.sif",
        "MODEL_DIR": "./models", "OPEN_WEBUI_DATA_DIR": "./data/ui", "TOOL_AUDIT_DIR": "./data/audit",
        "SEARXNG_CACHE_DIR": "./data/cache", "DOCLING_ARTIFACTS_DIR": "./data/artifacts", "DOCLING_AUDIT_DIR": "./data/docling-audit",
        "WORKSPACE_DIR": str(tmp_path), "LLAMA_API_KEY": "a", "EMBEDDING_API_KEY": "b", "SEARXNG_SECRET": "c", "DOCLING_GATE_API_KEY": "d", "WEBUI_SECRET_KEY": "e",
        "TOOL_WRITE_MODE": "read_only", "TOOL_NETWORK_MODE": "isolated", "TOOL_BRIDGE_ENABLED": "false", "WEB_SEARCH_ENABLED": "true",
        "OPEN_WEBUI_PORT": "3000", "LLAMA_SERVER_PORT": "8080", "EMBEDDING_SERVER_PORT": "8081", "TOOL_BRIDGE_PORT": "8090", "SEARXNG_PORT": "8082", "DOCLING_GATE_PORT": "5001", "DOCLING_PORT": "5002",
        "DOCLING_GATE_POLL_SECONDS": "1", "DOCLING_GATE_MAX_WAIT_SECONDS": "1", "DOCLING_GATE_MAX_RETRIES": "1", "DOCLING_GATE_MAX_UNKNOWN_POLLS": "1", "DOCLING_GATE_IDLE_SECONDS": "0",
    }
    return values


def test_optional_tool_settings_are_not_required(tmp_path):
    source = valid_values(tmp_path)
    for name in ("TOOL_WRITE_MODE", "TOOL_NETWORK_MODE", "WORKSPACE_DIR", "TOOL_AUDIT_DIR"):
        source.pop(name)
    values = config_check.validate(source)
    assert values["TOOL_BRIDGE_ENABLED"] == "false"


def test_duplicate_ports_are_rejected(tmp_path):
    values = valid_values(tmp_path)
    values["DOCLING_PORT"] = values["OPEN_WEBUI_PORT"]
    with pytest.raises(config_check.ConfigError, match="unique port"):
        config_check.validate(values)


def test_enabled_tool_requires_its_settings(tmp_path):
    values = valid_values(tmp_path)
    values["TOOL_BRIDGE_ENABLED"] = "true"
    with pytest.raises(config_check.ConfigError, match="TOOL_IMAGE"):
        config_check.validate(values)
