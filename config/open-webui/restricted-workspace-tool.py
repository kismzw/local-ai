"""
title: Restricted Workspace Review
author: Local AI
version: 1.0.0
license: MIT
description: Read-only Python, Git, and shell inspection in the isolated Apptainer workspace and data mounts.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Tools:
    def run_in_restricted_workspace(self, command: str, timeout_seconds: int = 60) -> str:
        """Run a read-only inspection command in the restricted sandbox.

        Use /workspace for approved code and /data for approved read-only data.
        The sandbox has Python, Git, and shell utilities. It has no user home,
        SSH material, GPU, arbitrary host mounts, or network access. Do not use
        this for modifications: every request is forced to read-only mode. Keep
        commands targeted: do not dump entire repositories or large files.
        """
        bridge_url = os.environ.get("TOOL_BRIDGE_URL", "http://127.0.0.1:8090/run")
        api_key = os.environ.get("TOOL_SANDBOX_API_KEY", "")
        if not api_key:
            return "Tool bridge is not configured: missing TOOL_SANDBOX_API_KEY."

        payload = json.dumps(
            {
                "command": command,
                "mode": "read",
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
            return f"Restricted sandbox rejected the request ({error.code}): {error.read().decode('utf-8', 'replace')}"
        except URLError as error:
            return f"Restricted sandbox is unavailable: {error.reason}"

        return json.dumps(
            {
                "exit_code": result.get("exit_code"),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
            },
            ensure_ascii=False,
        )
