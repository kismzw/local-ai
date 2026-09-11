# Security

The web interface, inference servers, and tool bridge bind to `127.0.0.1` by
default. Each API uses a generated bearer key. For remote access, expose only
Open WebUI through an authenticated private overlay such as Tailscale.

`data/open-webui` contains chats, uploads, RAG data, and the database. `.env`
contains keys. Both are sensitive and excluded from Git. The tool SIF has no
host-home, SSH/credential mount, GPU, or Docker socket; it is temporary-write
root plus the explicit workspace bind and, if configured, a separate read-only
`/data` bind. `TOOL_HIDDEN_PATHS` masks known secret files below `/workspace`.
This is containment, not a VM.

Audit logs live in `data/tool-audit`. Keep `TOOL_BRIDGE_ENABLED=false` to remove
tool execution from the system entirely. With `TOOL_WRITE_MODE=read_write`, the
Qwen Codex tool deliberately has unrestricted command execution within the
configured `/workspace` bind; it can delete or commit files there. The
plan-before-edit rule is a model workflow, not an access-control boundary.
Tool commands are serialized globally so a concurrent request cannot observe or
mutate a workspace during another command. Write requests first verify that the
audit log is writable; if recording the final result still fails, the response
states that the command completed and that auditing failed, so callers must not
blindly retry a mutation.

The tool SIF's Python base image is digest-pinned and its apt packages resolve
through a fixed Debian snapshot. Its local receipt verifies the built artifact
and definition hash before every systemd-backed startup.

The optional Full Desktop Shell is deliberately outside this containment model.
When `HOST_TOOL_ENABLED=true`, authenticated requests execute as the owner
Linux user, with that user's filesystem, process, network, and available SSH
agent authority. It is loopback-only, separately keyed, serialized, and emits
a best-effort operational audit, but it is not a sandbox. The audit is not
tamper-resistant against Full Desktop Shell itself: the command has the same
user-level authority over its JSONL file. Tamper resistance requires a separate
privilege boundary or remote append-only collector. Keep it disabled for
web-research profiles.

Before each Full Desktop command, the bridge overlays the current user
manager's `SSH_AUTH_SOCK`, display, runtime-directory, and D-Bus session
variables. This avoids retaining a stale agent socket after login auto-start.
Both bridges continuously drain command output into bounded tail buffers rather
than buffering arbitrary stdout/stderr in service memory. Host audit directories
and their active JSONL files are forced to owner-only `0700`/`0600` modes.

Open WebUI's automatic memory feature is disabled. Long-term memory follows the
explicit, owner-maintained YAML workflow in `docs/MEMORY.md`. Signups are also
disabled after the first administrator account. The UI has a 50 MB, ten-file
upload limit and allows only the document/source types needed for local RAG.
On this workstation, `tests/tool-isolation.sh` verified that an unprivileged
`--net --network none` run blocks DNS/egress, and the bridge is configured to
use it. Re-run the test after an Apptainer, kernel, or site-policy change. If it
fails, **NETWORK ISOLATION: NOT GUARANTEED**; keep any network-capable
autonomous tool behind explicit owner approval.

Web search intentionally changes the privacy boundary: SearXNG sends search
queries to public search engines and Open WebUI fetches selected public pages.
Those services bind only to loopback and use `--cleanenv --containall --no-home`
with explicit cache/artifact binds, but Apptainer host networking does not give
them reliable outbound network isolation. Open WebUI keeps private/local URL
fetching disabled and blocks redirects; do not enable `ENABLE_RAG_LOCAL_WEB_FETCH`.
Search results are cited in chats and are not automatically retained as
Knowledge.
