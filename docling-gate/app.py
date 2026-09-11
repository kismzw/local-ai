"""Loopback Docling proxy that prioritizes active llama.cpp inference."""
from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response

APP = FastAPI(title="Local AI Docling Gate", version="0.1.0")
GATE_LOCK = asyncio.Lock()
PROCESSING_METRIC = re.compile(
    r"^(?:llamacpp|llama)[a-zA-Z0-9_:]*(?:slots|requests)[a-zA-Z0-9_:]*(?:processing|predicting)[a-zA-Z0-9_:]*\s+([0-9.]+)$",
    re.MULTILINE,
)
DROP_HEADERS = {"host", "content-length", "authorization", "connection", "x-api-key"}


class InferenceState(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    UNKNOWN = "unknown"


def setting(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing required Docling gate setting: {name}")
    return value


def integer(name: str) -> int:
    return int(setting(name))


def append_audit(event: dict) -> None:
    directory = Path(setting("DOCLING_AUDIT_DIR"))
    directory.mkdir(parents=True, exist_ok=True)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from log_rotate import rotate_from_environment
    target = directory / "docling-gate.jsonl"
    rotate_from_environment(target)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def require_key(authorization: str | None, x_api_key: str | None) -> None:
    """Accept Open WebUI's documented X-Api-Key and a bearer key for probes.

    Open WebUI 0.11.0's Docling loader sends ``X-Api-Key`` rather than an
    Authorization header.  Supporting both keeps the loopback gate usable by
    the application and preserves the bearer form for direct operational use.
    """
    expected = setting("DOCLING_GATE_API_KEY")
    bearer_ok = authorization is not None and secrets.compare_digest(authorization, f"Bearer {expected}")
    api_key_ok = x_api_key is not None and secrets.compare_digest(x_api_key, expected)
    if not bearer_ok and not api_key_ok:
        raise HTTPException(status_code=401, detail="invalid Docling gate API key")


async def inference_state(client: httpx.AsyncClient) -> InferenceState:
    headers = {"Authorization": f"Bearer {setting('LLAMA_METRICS_API_KEY')}"}
    try:
        response = await client.get(
            setting("LLAMA_SLOTS_URL"), headers=headers
        )
        if response.is_success:
            slots = response.json()
            if isinstance(slots, list):
                if not slots:
                    pass
                elif all(isinstance(slot, dict) and isinstance(slot.get("is_processing"), bool) for slot in slots):
                    return InferenceState.BUSY if any(slot["is_processing"] for slot in slots) else InferenceState.IDLE
    except (httpx.HTTPError, ValueError):
        pass

    # Preserve the metrics probe as a compatible fallback for older llama.cpp
    # servers without /slots. The current server has /slots, which accurately
    # covers both prompt ingestion and token generation.
    try:
        response = await client.get(setting("LLAMA_METRICS_URL"), headers=headers)
        if response.status_code >= 400:
            return InferenceState.UNKNOWN
    except httpx.HTTPError:
        return InferenceState.UNKNOWN
    try:
        values = PROCESSING_METRIC.findall(response.text)
        if not values:
            return InferenceState.UNKNOWN
        return InferenceState.BUSY if any(float(value) > 0 for value in values) else InferenceState.IDLE
    except ValueError:
        return InferenceState.UNKNOWN


async def inference_is_busy(client: httpx.AsyncClient) -> bool:
    """Compatibility predicate for callers that only need an affirmative busy state."""
    return await inference_state(client) is InferenceState.BUSY


async def wait_for_inference_idle(client: httpx.AsyncClient) -> None:
    idle_since: float | None = None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + integer("DOCLING_GATE_MAX_WAIT_SECONDS")
    unknown_polls = 0
    while loop.time() < deadline:
        state = await inference_state(client)
        if state is InferenceState.BUSY:
            idle_since = None
            unknown_polls = 0
        elif state is InferenceState.IDLE:
            unknown_polls = 0
            idle_since = idle_since or loop.time()
            if loop.time() - idle_since >= integer("DOCLING_GATE_IDLE_SECONDS"):
                return
        else:
            idle_since = None
            unknown_polls += 1
            if unknown_polls >= integer("DOCLING_GATE_MAX_UNKNOWN_POLLS"):
                raise HTTPException(status_code=503, detail="Docling cannot verify inference availability")
        await asyncio.sleep(integer("DOCLING_GATE_POLL_SECONDS"))
    raise HTTPException(status_code=503, detail="Docling is waiting for inference to become idle")


def upstream_headers(request: Request) -> dict[str, str]:
    return {key: value for key, value in request.headers.items() if key.lower() not in DROP_HEADERS}


def is_cuda_oom(response: httpx.Response) -> bool:
    if response.status_code < 500:
        return False
    text = response.text.lower()
    return "cuda out of memory" in text or "out of memory" in text


@APP.get("/health")
@APP.get("/health/live")
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": setting("DOCLING_BACKEND_URL")}


@APP.get("/health/ready")
async def ready() -> dict[str, str]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{setting('DOCLING_BACKEND_URL').rstrip('/')}/health")
        if not response.is_success:
            raise HTTPException(status_code=503, detail="Docling backend is unavailable")
    except httpx.HTTPError as error:
        raise HTTPException(status_code=503, detail="Docling backend is unavailable") from error
    return {"status": "ready"}


@APP.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(
    path: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> Response:
    require_key(authorization, x_api_key)
    body = await request.body()
    started = datetime.now(timezone.utc)
    started_monotonic = asyncio.get_running_loop().time()
    timeout = httpx.Timeout(float(integer("DOCLING_GATE_MAX_WAIT_SECONDS") + 60))
    response: httpx.Response | None = None
    attempts = 0
    failure: str | None = None
    try:
        async with GATE_LOCK:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for attempts in range(1, integer("DOCLING_GATE_MAX_RETRIES") + 1):
                    await wait_for_inference_idle(client)
                    response = await client.request(
                        request.method, f"{setting('DOCLING_BACKEND_URL').rstrip('/')}/{path}",
                        params=request.query_params, content=body, headers=upstream_headers(request),
                    )
                    if not is_cuda_oom(response) or attempts == integer("DOCLING_GATE_MAX_RETRIES"):
                        break
                    await asyncio.sleep(integer("DOCLING_GATE_POLL_SECONDS"))
    except (httpx.HTTPError, HTTPException) as error:
        failure = str(getattr(error, "detail", error))
        status = error.status_code if isinstance(error, HTTPException) else 503
        raise HTTPException(status_code=status, detail=failure) from error
    finally:
        try:
            append_audit({"at": started.isoformat(), "method": request.method, "path": f"/{path}",
                          "status": response.status_code if response else 503, "bytes": len(body),
                          "retry_count": max(0, attempts - 1), "duration_ms": round((asyncio.get_running_loop().time() - started_monotonic) * 1000),
                          "failure": failure})
        except OSError:
            # Conversion result remains authoritative if the audit filesystem is full.
            pass
    assert response is not None
    headers = {key: value for key, value in response.headers.items() if key.lower() in {"content-type", "content-disposition"}}
    return Response(content=response.content, status_code=response.status_code, headers=headers)
