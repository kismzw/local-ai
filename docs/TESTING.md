# Testing

Run `./tests/smoke.sh` after the native services are healthy. It validates model discovery,
non-streaming and SSE chat, GPU visibility, UI health, embeddings, and core
sandbox execution/isolation. `./scripts/doctor.sh` gives a broader operator
check. Track results in `docs/ACCEPTANCE.md` rather than inferring them from
configuration alone.

`smoke.sh` runs the writable Codex workflow only when both
`TOOL_BRIDGE_ENABLED=true` and `TOOL_WRITE_MODE=read_write`; read-only bridge
configurations still validate containment and allowlisted mounts.

## Automated web-fetch boundary check

With the native Open WebUI service running, execute:

```bash
./tests/web-fetch-isolation.sh
```

It imports the pinned Open WebUI URL validator with a disposable data directory
and proves that loopback, RFC1918, IPv6-private, and metadata URLs are refused.
It also verifies redirects are disabled. This is a policy-level check; repeat
the browser/API probes below after an Open WebUI upgrade.

Manual deterministic checks:

1. Create a user, chat, restart with `./scripts/stop.sh && ./scripts/start.sh`, and confirm the chat remains.
2. Follow `docs/RAG.md` and confirm the validation code is retrieved only with its collection enabled. Repeat with a scanned Japanese/English PDF and a table-heavy PDF after confirming the Docling preview contains the expected text/cells.
3. Add the bundled `qwen_codex_workspace` native adapter, create Qwen Codex, and ask it for a small change. Confirm it inspects, presents a plan, and makes no write call until an explicit approval reply. Then confirm it reports a diff, checks, and a commit hash.
4. With `TOOL_BRIDGE_ENABLED=true`, run `./tests/tool-isolation.sh`, `./tests/tool-bridge-allowlist.sh`, and `./tests/tool-bridge-codex.sh`; they prove host-path isolation, a read-only `/workspace` mount with an actual failed write, optional `/data:ro` with an actual failed write, secret-path masking, authenticated writable commands, output capping, and contained Git behavior. Record whether unprivileged network namespaces work. Tool checks are intentionally skipped by `smoke.sh` while the bridge is disabled.
5. Verify Qwen Fast/Think/Research/Codex are present after following `config/open-webui/model-profiles.md`.
6. Change only endpoint/model variables in a copy of `.env` to prove backend replacement does not require UI changes.
7. Follow `config/open-webui/web-search.md`, including **Settings → Interface → Web Search in Chat → Always**, ask a current question in each profile, and confirm cited source links appear. Confirm a normal timeless question does not require a search.
8. Attempt a URL fetch for `http://127.0.0.1:8080`, `http://10.0.0.1`, and a redirect to a local address; each must be rejected. `tests/tool-isolation.sh` must still show no tool-container egress.
