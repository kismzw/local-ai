# Add the restricted tool bridge

Start it only after reviewing the workspace and network settings in `.env`:

Set `TOOL_BRIDGE_ENABLED=true` in `.env`, then run:

```bash
./scripts/start-tool-bridge.sh
```

In Open WebUI, create an external OpenAPI tool from
`http://127.0.0.1:8090/openapi.json`. Use bearer authentication with the value
of `TOOL_SANDBOX_API_KEY`. The bridge exposes one operation, `POST /run`.

Use `mode: read` for inspection; its `/workspace` mount is truly read-only.
`mode: write` succeeds only when the owner has explicitly set
`TOOL_WRITE_MODE=read_write` in `.env`; every invocation is recorded in
`data/tool-audit/tool-bridge.jsonl`. Never set `TOOL_NETWORK_MODE`
to `isolated` until `tests/tool-isolation.sh` demonstrates the local Apptainer
configuration can create an unprivileged network namespace.
