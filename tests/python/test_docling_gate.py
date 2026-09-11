from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("docling_gate_app", ROOT / "docling-gate/app.py")
gate = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(gate)


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("LLAMA_METRICS_API_KEY", "key")
    monkeypatch.setenv("LLAMA_SLOTS_URL", "http://llama/slots")
    monkeypatch.setenv("LLAMA_METRICS_URL", "http://llama/metrics")
    monkeypatch.setenv("DOCLING_GATE_IDLE_SECONDS", "0")
    monkeypatch.setenv("DOCLING_GATE_POLL_SECONDS", "1")
    monkeypatch.setenv("DOCLING_GATE_MAX_WAIT_SECONDS", "30")
    monkeypatch.setenv("DOCLING_GATE_MAX_UNKNOWN_POLLS", "3")
    monkeypatch.setenv("DOCLING_GATE_MAX_RETRIES", "2")
    monkeypatch.setenv("DOCLING_GATE_API_KEY", "gate-key")
    monkeypatch.setenv("DOCLING_BACKEND_URL", "http://docling")
    monkeypatch.setenv("DOCLING_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_MAX_BYTES", "100000")
    monkeypatch.setenv("LOG_ROTATION_COUNT", "2")


async def state_for(slots: httpx.Response | Exception, metrics: httpx.Response | Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        item = slots if request.url.path == "/slots" else metrics
        if isinstance(item, Exception):
            raise item
        return item
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await gate.inference_state(client)


@pytest.mark.anyio
async def test_slots_busy_and_idle():
    assert await state_for(httpx.Response(200, json=[{"is_processing": True}]), httpx.Response(200)) is gate.InferenceState.BUSY
    assert await state_for(httpx.Response(200, json=[{"is_processing": False}]), httpx.Response(200)) is gate.InferenceState.IDLE


@pytest.mark.anyio
async def test_metrics_fallback_busy_idle_and_malformed():
    error = httpx.ConnectError("slots down")
    assert await state_for(error, httpx.Response(200, text="llamacpp_slots_processing 1\n")) is gate.InferenceState.BUSY
    assert await state_for(error, httpx.Response(200, text="llamacpp_slots_processing 0\n")) is gate.InferenceState.IDLE
    assert await state_for(error, httpx.Response(200, text="not prometheus")) is gate.InferenceState.UNKNOWN


@pytest.mark.anyio
async def test_unknown_slots_schema_falls_back_to_metrics():
    slots = httpx.Response(200, json=[{"unexpected": "value"}])
    assert await state_for(slots, httpx.Response(200, text="llamacpp_slots_processing 1\n")) is gate.InferenceState.BUSY


@pytest.mark.anyio
async def test_unknown_probe_fails_safe(monkeypatch):
    async def unknown(_client):
        return gate.InferenceState.UNKNOWN
    async def no_sleep(_seconds):
        return None
    monkeypatch.setattr(gate, "inference_state", unknown)
    monkeypatch.setattr(gate.asyncio, "sleep", no_sleep)
    async with httpx.AsyncClient() as client:
        with pytest.raises(gate.HTTPException) as error:
            await gate.wait_for_inference_idle(client)
    assert error.value.status_code == 503


def test_authentication_and_header_filtering():
    gate.require_key("Bearer gate-key", None)
    gate.require_key(None, "gate-key")
    with pytest.raises(gate.HTTPException):
        gate.require_key("Bearer nope", None)

    async def receive():
        return {"type": "http.request", "body": b"x", "more_body": False}

    request = Request(
        {
            "type": "http", "method": "POST", "path": "/convert", "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer gate-key"), (b"x-api-key", b"gate-key"),
                (b"host", b"gate.local"), (b"content-length", b"1"),
                (b"x-custom", b"preserve-me"),
            ],
        },
        receive,
    )
    assert gate.upstream_headers(request) == {"x-custom": "preserve-me"}


@pytest.mark.anyio
async def test_oom_retry_waits_for_idle_before_every_attempt(monkeypatch):
    waits = 0
    responses = [httpx.Response(500, text="CUDA out of memory"), httpx.Response(200, content=b"ok")]

    async def wait(_client):
        nonlocal waits
        waits += 1

    async def no_sleep(_seconds):
        return None

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, *_args, **_kwargs):
            return responses.pop(0)

    async def receive():
        return {"type": "http.request", "body": b"payload", "more_body": False}

    monkeypatch.setattr(gate, "wait_for_inference_idle", wait)
    monkeypatch.setattr(gate.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(gate.httpx, "AsyncClient", lambda **_kwargs: Client())
    request = Request({"type": "http", "method": "POST", "path": "/convert", "headers": [], "query_string": b""}, receive)
    result = await gate.proxy("convert", request, authorization="Bearer gate-key", x_api_key=None)
    assert result.status_code == 200
    assert waits == 2
