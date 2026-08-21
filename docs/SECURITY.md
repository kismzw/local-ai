# Security

The web interface, inference servers, and tool bridge bind to `127.0.0.1` by
default. Each API uses a generated bearer key. For remote access, expose only
Open WebUI through an authenticated private overlay such as Tailscale.

`data/open-webui` contains chats, uploads, RAG data, and the database. `.env`
contains keys. Both are sensitive and excluded from Git. The tool SIF has no
host-home, SSH/credential mount, GPU, or Docker socket; it is temporary-write
root plus the single explicit workspace bind. This is containment, not a VM.

Audit logs live in `data/tool-audit`. Keep `TOOL_BRIDGE_ENABLED=false` to remove
tool execution from the system entirely.

Open WebUI's automatic memory feature is disabled. Long-term memory follows the
explicit, owner-maintained YAML workflow in `docs/MEMORY.md`. Signups are also
disabled after the first administrator account. The UI has a 50 MB, ten-file
upload limit and allows only the document/source types needed for local RAG.
On this workstation, `tests/tool-isolation.sh` verified that an unprivileged
`--net --network none` run blocks DNS/egress, and the bridge is configured to
use it. Re-run the test after an Apptainer, kernel, or site-policy change. If it
fails, **NETWORK ISOLATION: NOT GUARANTEED**; keep any network-capable
autonomous tool behind explicit owner approval.
