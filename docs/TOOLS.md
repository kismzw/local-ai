# Tools

The native localhost tool bridge starts a separate immutable Apptainer SIF with
Python, bash, and git. Open WebUI has a read-only review adapter and **Qwen
Codex Workspace**, which provides separate inspection and modification tools.
Add them as described in `config/open-webui/tool-bridge.md`. The bridge is
disabled by default and must be explicitly enabled for the configured workspace.

The tool SIF runs with `--cleanenv --containall --no-home --writable-tmpfs`; it
does not receive GPU, host home, SSH keys, credentials, Docker socket, or host
configuration. `/workspace` maps only `WORKSPACE_DIR`. Read calls mount it
`:ro`; Codex write calls mount it `:rw` when `TOOL_WRITE_MODE=read_write`.
Write execution is fully unrestricted within that explicit mount, including
recursive deletion, package commands, and Git commits. Python
scratch work is temporary. Audit logs are retained in `data/tool-audit`.

`TOOL_DATA_DIR`, when explicitly set by the owner, is a second bind mounted at
`/data:ro`; it can be searched but never modified through the container. Use
`TOOL_HIDDEN_PATHS` for any secret file below `WORKSPACE_DIR`: each listed
absolute path is replaced inside the container by an empty read-only file.

`TOOL_MAX_OUTPUT_CHARS` limits the combined sandbox result retained in each
chat tool call (default `6000`). This prevents repeated repository listings
from exhausting the model context; use targeted `rg` and `sed` commands for
review work.

On this workstation the unprivileged `--net --network none` probe passed, so
the configured bridge uses
`TOOL_NETWORK_MODE=isolated`. Re-run `tests/tool-isolation.sh` after an
Apptainer or host-policy change. If that probe does not pass on another host,
**NETWORK ISOLATION: NOT GUARANTEED** and network-capable tool activity must
remain behind owner approval.

The core chat/RAG services do not depend on bridge health; if tools are stopped
or disabled, Open WebUI remains usable normally.

## Full Desktop Shell

The optional **Full Desktop Shell** is a different service from the contained
tool bridge. With `HOST_TOOL_ENABLED=true`, it runs `/bin/bash -lc` as the
owner Linux user in `HOST_TOOL_CWD`, without Apptainer containment. It can use
the user's files, local programs, network, and imported `SSH_AUTH_SOCK`.
Every command requires the separate `HOST_TOOL_API_KEY`, flushes a `start`
audit event before execution, and creates a completion event afterward in
`data/host-tool-audit/host-bridge.jsonl`. This is a best-effort operational
audit, not a tamper-resistant trail: the Full Desktop Shell has the same user
authority as the audit file. It is intentionally not read-only. Enable it only
for the Local Admin model profile, never as a default companion to web research.

The bridge obtains current session variables from `systemctl --user
show-environment` for every command, so a login-time service does not retain an
obsolete SSH-agent socket after the session updates it. Command stdout/stderr
is continuously drained into bounded tail buffers. Custom host-audit paths are
enforced as `0700`, with the active JSONL file at `0600`.

Qwen Codex follows a chat-level approval protocol: it inspects first, presents a
plan, and waits for an explicit approval before write calls. Open WebUI cannot
technically attest that a preceding approval message was user-authored, so do
not treat this as a security boundary. After relevant checks pass, it commits
each changed Git repository separately. If local repository identity is absent,
it asks for a name/email and uses temporary `git -c` options rather than saving
them.
