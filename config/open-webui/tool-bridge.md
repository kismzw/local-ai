# Add the restricted tool bridge

Start it only after reviewing the workspace, optional read-only data source,
secret-mask list, and network settings in `.env`:

Set `TOOL_BRIDGE_ENABLED=true` in `.env`, then run:

```bash
./scripts/start-tool-bridge.sh
```

Open WebUI 0.11.0 does not reliably persist the OpenAPI tool-server connection,
so use a bundled native adapter instead. For read-only investigation, create a
tool with id `restricted_workspace`, paste
`config/open-webui/restricted-workspace-tool.py`, and enable it in a chat. For
the coding agent, create a separate tool with id `qwen_codex_workspace`, paste
`config/open-webui/qwen-codex-tool.py`, and enable it only for Qwen Codex. The
Codex adapter exposes separate read and write functions and retrieves the bridge
credential from the native Open WebUI process environment; the model never sees
the credential.

The bridge itself still exposes `http://127.0.0.1:8090/openapi.json` for a
future Open WebUI release with stable OpenAPI tool-server support.

Use the restricted adapter for read-only inspection. The Qwen Codex write tool
needs `TOOL_WRITE_MODE=read_write`; every invocation is recorded in
`data/tool-audit/tool-bridge.jsonl`. Its commands are unrestricted inside the
contained `/workspace` mount, so they can delete workspace files, run project
package managers, and make Git commits. Never set `TOOL_NETWORK_MODE`
to `isolated` until `tests/tool-isolation.sh` demonstrates the local Apptainer
configuration can create an unprivileged network namespace.

Set `TOOL_DATA_DIR` only for an explicitly approved directory. It is exposed as
`/data:ro` for both read and write calls, so a tool can search or analyse data
without modifying it. If a workspace necessarily contains a secret file, list
its absolute path in `TOOL_HIDDEN_PATHS`; the bridge verifies it is inside
`WORKSPACE_DIR` and mounts an empty read-only file over it.
