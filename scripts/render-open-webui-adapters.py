#!/usr/bin/env python3
"""Render standalone Open WebUI adapters from one audited template."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "config/open-webui/templates/adapter.py.tmpl").read_text()
COMMON = '''    def _run(self, command: str, mode: str, timeout_seconds: int) -> str:
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
'''
VARIANTS = {
    "qwen-codex-tool.py": ("Qwen Codex Workspace", "Inspect and modify the explicitly configured local coding workspace through the contained Apptainer bridge.", COMMON + '''
    def inspect_workspace(self, command: str, timeout_seconds: int = 60) -> str:
        """Inspect /workspace without modifying it; use before proposing a plan."""
        return self._run(command, "read", timeout_seconds)

    def modify_workspace(self, command: str, timeout_seconds: int = 120) -> str:
        """Modify /workspace only after explicit user approval; then test and report the diff."""
        return self._run(command, "write", timeout_seconds)
'''),
    "restricted-workspace-tool.py": ("Restricted Workspace Review", "Read-only Python, Git, and shell inspection in the isolated Apptainer workspace and optional data mounts.", COMMON + '''
    def run_in_restricted_workspace(self, command: str, timeout_seconds: int = 60) -> str:
        """Run a targeted read-only command in /workspace or optional /data."""
        return self._run(command, "read", timeout_seconds)
'''),
}


def render() -> dict[Path, str]:
    return {
        ROOT / "config/open-webui" / name: (
            TEMPLATE.replace("{{TITLE}}", title)
            .replace("{{DESCRIPTION}}", description)
            .replace("{{METHODS}}", methods)
            .rstrip()
            + "\n"
        )
        for name, (title, description, methods) in VARIANTS.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for path, text in render().items():
        if args.check:
            if not path.exists() or path.read_text() != text:
                mismatches.append(path)
        else:
            path.write_text(text)
    if mismatches:
        print("Generated adapters are stale: " + ", ".join(str(path.relative_to(ROOT)) for path in mismatches))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
