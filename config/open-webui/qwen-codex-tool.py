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

        payload = json.dumps(
            {
                "command": command,
                "mode": mode,
                "timeout_seconds": max(1, min(int(timeout_seconds), 300)),
            }
        ).encode("utf-8")
        request = Request(
            bridge_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=305) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return f"Workspace sandbox rejected the request ({error.code}): {error.read().decode('utf-8', 'replace')}"
        except URLError as error:
            return f"Workspace sandbox is unavailable: {error.reason}"

        return json.dumps(
            {
                "exit_code": result.get("exit_code"),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            },
            ensure_ascii=False,
        )

    def inspect_workspace(self, command: str, timeout_seconds: int = 60) -> str:
        """Inspect the configured coding workspace without modifying it.

        Run targeted shell, Python, and Git inspection commands from /workspace.
        Use this before proposing a plan. The sandbox has no network, host home,
        SSH material, GPU, Docker socket, or arbitrary host mounts.
        """
        return self._run(command, "read", timeout_seconds)

    def modify_workspace(self, command: str, timeout_seconds: int = 120) -> str:
        """Modify the configured coding workspace after the user approved the plan.

        This can run normal project commands, edit files, execute tests, and use
        Git. Before calling it, present a concise plan and wait for an explicit
        user approval in the chat. Keep work inside /workspace. After successful
        relevant checks, commit each changed Git repository separately. If a
        repository has no local Git identity, ask the user for name and email;
        pass them with git -c user.name=... -c user.email=... and never persist
        them. Do not commit if checks fail; report the failure and leave edits.
        """
        return self._run(command, "write", timeout_seconds)
