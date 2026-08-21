# Tools

The native localhost tool bridge starts a separate immutable Apptainer SIF with
Python, bash, and git. Add its OpenAPI definition in Open WebUI as described in
`config/open-webui/tool-bridge.md`. It is disabled by default.

The tool SIF runs with `--cleanenv --containall --no-home --writable-tmpfs`; it
does not receive GPU, host home, SSH keys, credentials, Docker socket, or host
configuration. `/workspace` maps only `WORKSPACE_DIR`. It is mounted writable
only because the user explicitly configured that exact directory; read calls
mount it `:ro`, and write calls are rejected unless `TOOL_WRITE_MODE=read_write`
is deliberately set. Python
scratch work is temporary. Audit logs are retained in `data/tool-audit`.

The first milestone rejects destructive Git commands, package installation,
`sudo`, and host/container-management commands. On this workstation the
unprivileged `--net --network none` probe passed, so the configured bridge uses
`TOOL_NETWORK_MODE=isolated`. Re-run `tests/tool-isolation.sh` after an
Apptainer or host-policy change. If that probe does not pass on another host,
**NETWORK ISOLATION: NOT GUARANTEED** and network-capable tool activity must
remain behind owner approval.

The core chat/RAG services do not depend on bridge health; if tools are stopped
or disabled, Open WebUI remains usable normally.
