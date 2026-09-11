"""
title: Qwen Codex Workspace
author: Local AI
version: 1.0.0
license: MIT
description: Inspect and modify the explicitly configured local coding workspace through the contained Apptainer bridge.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Tools:
    def _run(self, command: str, mode: str, timeout_seconds: int) -> str:
        bridge_url = os.environ.get("TOOL_BRIDGE_URL", "http://127.0.0.1:8090/run")
        api_key = os.environ.get("TOOL_SANDBOX_API_KEY", "")
        if not api_key:
            return "Tool bridge is not configured: missing TOOL_SANDBOX_API_KEY."
        payload = json.dumps({"command": command, "mode": mode, "timeout_seconds": max(1, min(int(timeout_seconds), 300))}).encode("utf-8")
        request = Request(bridge_url, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=305) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return f"Workspace sandbox rejected the request ({error.code}): {error.read().decode('utf-8', 'replace')}"
        except URLError as error:
            return f"Workspace sandbox is unavailable: {error.reason}"
        return json.dumps({"exit_code": result.get("exit_code"), "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}, ensure_ascii=False)

    def inspect_workspace(self, command: str, timeout_seconds: int = 60) -> str:
        """Inspect /workspace without modifying it; use before proposing a plan."""
        return self._run(command, "read", timeout_seconds)

    def modify_workspace(self, command: str, timeout_seconds: int = 120) -> str:
        """Modify /workspace only after explicit user approval; then test and report the diff."""
        return self._run(command, "write", timeout_seconds)
