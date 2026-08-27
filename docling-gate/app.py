"""Loopback Docling proxy that prioritizes active llama.cpp inference."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response

APP = FastAPI(title="Local AI Docling Gate", version="0.1.0")
GATE_LOCK = asyncio.Lock()
PROCESSING_METRIC = re.compile(
    r"^(?:llamacpp|llama)[a-zA-Z0-9_:]*(?:slots|requests)[a-zA-Z0-9_:]*(?:processing|predicting)[a-zA-Z0-9_:]*\\s+([0-9.]+)$",
    re.MULTILINE,
)
DROP_HEADERS = {"host", "content-length", "authorization", "connection", "x-api-key"}


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
    with (directory / "docling-gate.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def require_key(authorization: str | None, x_api_key: str | None) -> None:
    """Accept Open WebUI's documented X-Api-Key and a bearer key for probes.

    Open WebUI 0.11.0's Docling loader sends ``X-Api-Key`` rather than an
    Authorization header.  Supporting both keeps the loopback gate usable by
    the application and preserves the bearer form for direct operational use.
    """
    expected = setting("DOCLING_GATE_API_KEY")
    if authorization != f"Bearer {expected}" and x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid Docling gate API key")


async def inference_is_busy(client: httpx.AsyncClient) -> bool:
    headers = {"Authorization": f"Bearer {setting('LLAMA_METRICS_API_KEY')}"}
    try:
        response = await client.get(
            setting("LLAMA_SLOTS_URL"), headers=headers
        )
        if response.is_success:
            slots = response.json()
            if isinstance(slots, list):
                return any(slot.get("is_processing", False) for slot in slots if isinstance(slot, dict))
    except httpx.HTTPError:
        pass

    # Preserve the metrics probe as a compatible fallback for older llama.cpp
    # servers without /slots. The current server has /slots, which accurately
    # covers both prompt ingestion and token generation.
    try:
        response = await client.get(setting("LLAMA_METRICS_URL"), headers=headers)
        if response.status_code >= 400:
            return False
    except httpx.HTTPError:
        return False
    return any(float(value) > 0 for value in PROCESSING_METRIC.findall(response.text))


async def wait_for_inference_idle(client: httpx.AsyncClient) -> None:
    idle_since: float | None = None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + integer("DOCLING_GATE_MAX_WAIT_SECONDS")
    while loop.time() < deadline:
        if await inference_is_busy(client):
            idle_since = None
        else:
            idle_since = idle_since or loop.time()
            if loop.time() - idle_since >= integer("DOCLING_GATE_IDLE_SECONDS"):
                return
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
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": setting("DOCLING_BACKEND_URL")}


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
    timeout = httpx.Timeout(float(integer("DOCLING_GATE_MAX_WAIT_SECONDS") + 60))
    async with GATE_LOCK:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await wait_for_inference_idle(client)
            response: httpx.Response | None = None
            for attempt in range(1, integer("DOCLING_GATE_MAX_RETRIES") + 1):
                response = await client.request(
                    request.method,
                    f"{setting('DOCLING_BACKEND_URL').rstrip('/')}/{path}",
                    params=request.query_params,
                    content=body,
                    headers=upstream_headers(request),
                )
                if not is_cuda_oom(response) or attempt == integer("DOCLING_GATE_MAX_RETRIES"):
                    break
                await asyncio.sleep(integer("DOCLING_GATE_POLL_SECONDS"))
    assert response is not None
    append_audit(
        {
            "at": started.isoformat(),
            "method": request.method,
            "path": f"/{path}",
            "status": response.status_code,
            "bytes": len(body),
        }
    )
    headers = {key: value for key, value in response.headers.items() if key.lower() in {"content-type", "content-disposition"}}
    return Response(content=response.content, status_code=response.status_code, headers=headers)
