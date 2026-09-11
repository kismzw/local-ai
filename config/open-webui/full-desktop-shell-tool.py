"""
title: Full Desktop Shell
author: Local AI
version: 1.0.0
license: MIT
description: Run arbitrary commands as the owner's Linux user. This can read, modify or delete any accessible file, start processes, access the network, and use SSH credentials available to the user session.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Tools:
    def run_full_desktop_command(self, command: str, timeout_seconds: int = 60) -> str:
        """Run an arbitrary command as the owner Linux user; it has full user-level authority."""
        bridge_url = os.environ.get("HOST_TOOL_BRIDGE_URL", "http://127.0.0.1:8091/run")
        api_key = os.environ.get("HOST_TOOL_API_KEY", "")
        if not api_key:
            return "Full Desktop Shell is not configured: missing HOST_TOOL_API_KEY."
        maximum = max(1, min(int(os.environ.get("HOST_TOOL_MAX_TIMEOUT_SECONDS", "300")), 3600))
        payload = json.dumps({"command": command, "timeout_seconds": max(1, min(int(timeout_seconds), maximum))}).encode("utf-8")
        request = Request(bridge_url, data=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=maximum + 5) as response:
                return json.dumps(json.loads(response.read().decode("utf-8")), ensure_ascii=False)
        except HTTPError as error:
            return f"Full Desktop Shell rejected the request ({error.code}): {error.read().decode('utf-8', 'replace')}"
        except URLError as error:
            return f"Full Desktop Shell is unavailable: {error.reason}"
