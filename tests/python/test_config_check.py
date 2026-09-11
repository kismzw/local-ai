from __future__ import annotations

import importlib.util
import os
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
        "MODEL_DIR": "./models", "DATA_DIR": "./data", "OPEN_WEBUI_DATA_DIR": "./data/ui", "TOOL_AUDIT_DIR": "./data/audit",
        "SEARXNG_CACHE_DIR": "./data/cache", "DOCLING_ARTIFACTS_DIR": "./data/artifacts", "DOCLING_AUDIT_DIR": "./data/docling-audit",
        "WORKSPACE_DIR": str(tmp_path), "LLAMA_API_KEY": "a", "EMBEDDING_API_KEY": "b", "SEARXNG_SECRET": "c", "DOCLING_GATE_API_KEY": "d", "WEBUI_SECRET_KEY": "e",
        "TOOL_WRITE_MODE": "read_only", "TOOL_NETWORK_MODE": "isolated", "TOOL_BRIDGE_ENABLED": "false", "WEB_SEARCH_ENABLED": "true", "OPEN_WEBUI_VERSION": "0.11.0",
        "OPEN_WEBUI_BIND": "127.0.0.1", "LLAMA_SERVER_BIND": "127.0.0.1", "TOOL_BRIDGE_BIND": "127.0.0.1",
        "OPEN_WEBUI_PORT": "3000", "LLAMA_SERVER_PORT": "8080", "EMBEDDING_SERVER_PORT": "8081", "TOOL_BRIDGE_PORT": "8090", "SEARXNG_PORT": "8082", "DOCLING_GATE_PORT": "5001", "DOCLING_PORT": "5002",
        "DOCLING_GATE_POLL_SECONDS": "1", "DOCLING_GATE_MAX_WAIT_SECONDS": "1", "DOCLING_GATE_MAX_RETRIES": "1", "DOCLING_GATE_MAX_UNKNOWN_POLLS": "1", "DOCLING_GATE_IDLE_SECONDS": "0", "DOCLING_MAX_SYNC_WAIT_SECONDS": "1", "LOG_MAX_BYTES": "1", "LOG_ROTATION_COUNT": "1",
        "MODEL_CONTEXT_SIZE": "1024", "MODEL_PARALLELISM": "1", "MODEL_GPU_LAYERS": "all", "MODEL_THREADS": "1", "MODEL_BATCH_SIZE": "1", "MODEL_UBATCH_SIZE": "1", "MODEL_KV_CACHE_K": "q8_0", "MODEL_KV_CACHE_V": "q8_0",
        "RAG_CHUNK_SIZE": "100", "RAG_CHUNK_OVERLAP": "0", "WEB_SEARCH_RESULT_COUNT": "1", "WEB_SEARCH_CONCURRENT_REQUESTS": "1", "WEB_LOADER_CONCURRENT_REQUESTS": "1", "WEB_LOADER_TIMEOUT_SECONDS": "1", "WEB_FETCH_MAX_CONTENT_LENGTH": "1",
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


def test_rag_alias_is_generated_from_models_toml(tmp_path):
    values = config_check.validate(valid_values(tmp_path))
    assert values["RAG_EMBEDDING_MODEL"] == values["EMBEDDING_MODEL_ALIAS"]


def test_rag_alias_override_is_rejected(tmp_path):
    values = valid_values(tmp_path)
    values["RAG_EMBEDDING_MODEL"] = "other"
    with pytest.raises(config_check.ConfigError, match="conflicts"):
        config_check.validate(values)


def test_invalid_rag_overlap_is_rejected(tmp_path):
    values = valid_values(tmp_path)
    values["RAG_CHUNK_OVERLAP"] = values["RAG_CHUNK_SIZE"]
    with pytest.raises(config_check.ConfigError, match="smaller"):
        config_check.validate(values)


def test_ipv6_loopback_is_rejected(tmp_path):
    values = valid_values(tmp_path)
    values["LLAMA_SERVER_BIND"] = "::1"
    with pytest.raises(config_check.ConfigError, match="loopback"):
        config_check.validate(values)


def test_tool_output_limit_has_a_safe_default(tmp_path):
    values = valid_values(tmp_path)
    values.pop("TOOL_MAX_OUTPUT_CHARS", None)
    assert config_check.validate(values)["TOOL_MAX_OUTPUT_CHARS"] == "6000"


def test_env_permissions_require_owner_only(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=value\n", encoding="utf-8")
    os.chmod(env_file, 0o600)
    config_check.validate_env_permissions(env_file)
    for mode in (0o640, 0o644):
        os.chmod(env_file, mode)
        with pytest.raises(config_check.ConfigError, match="owner-only"):
            config_check.validate_env_permissions(env_file)


def test_systemd_environment_is_created_owner_only(tmp_path):
    output = tmp_path / "run" / "local-ai.env"
    config_check.write_systemd_env(output, {"SECRET": "value"})
    assert output.read_text(encoding="utf-8") == 'SECRET="value"\n'
    assert output.stat().st_mode & 0o777 == 0o600


def test_open_webui_version_must_match_locked_runtime(tmp_path, monkeypatch):
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\ndependencies = ["open-webui==9.9.9"]\n', encoding="utf-8")
    monkeypatch.setattr(config_check, "OPEN_WEBUI_PROJECT", project)
    with pytest.raises(config_check.ConfigError, match="OPEN_WEBUI_VERSION"):
        config_check.validate(valid_values(tmp_path))
