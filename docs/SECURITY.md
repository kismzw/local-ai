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
