# Acceptance ledger

This ledger distinguishes implementation evidence from live evidence. Do not
claim a checked item until the listed live test has run on this host.

## Recorded live evidence — 2026-08-21 and 2026-08-26

| Check | Result |
| --- | --- |
| Apptainer GPU passthrough | Passed with Apptainer 1.3.4: CUDA 12.8 OCI probe and official llama.cpp SIF both see RTX 5090. |
| Inference API | Passed: localhost `/health`, `/v1/models`, chat completion, SSE stream, and `/metrics`. |
| 32k benchmark | 22.2 GiB VRAM with embedding service; TTFT 1.14 s; generation 65.7 tok/s; 23k-token prefill 3,322 tok/s / 7.33 s TTFT. [Reference](../benchmarks/reference/20260821-180158-32768.md) |
| 64k benchmark | Passed at 45.9k-token long prompt: 21.1 GiB VRAM without embedding server; TTFT 1.05 s; generation 65.2 tok/s; long prefill 2,905 tok/s / 16.20 s TTFT. [Reference](../benchmarks/reference/20260821-180229-65536.md) |
| Native Open WebUI | Passed: user-space Python 3.11 service answered `GET /health` on 127.0.0.1:3000. |
| Embeddings | Passed: Qwen3 Embedding `/v1/embeddings` returned a vector. |
| SearXNG | Passed: official Apptainer SIF binds to 127.0.0.1:8082 and returned JSON search results. |
| Web-fetch SSRF policy | Passed against the pinned Open WebUI validator: localhost, RFC1918, IPv6-private, and metadata targets were rejected; redirect following is disabled. |
| Docling service | Passed: official CUDA SIF sees the GPU, initializes local artifacts, a gated upload using Open WebUI's `X-Api-Key` returned extracted text, and the gate detected an active llama.cpp slot. |
| Tool filesystem isolation | Re-run required after the corrected allowlist test: it now proves `/workspace:ro` and optional `/data:ro` with failed writes, plus masking and positive adjacent-file visibility. |
| Tool network behavior | Passed: unprivileged `--net --network none` blocked DNS/egress. `TOOL_NETWORK_MODE=isolated` is set for this host. |
| Codex tool bridge | Passed: authenticated contained write commands created separate Git commits, an identity-free commit failed, and command output was capped and audited. |

Not yet browser-verified: initial-admin login, model-profile creation, chat
survival across a restart, PDF Knowledge collection grounding, and OpenAPI-tool
import. Web Search capability/default-feature persistence and a Docling-backed
Knowledge upload also require the owner to complete first login in the browser.

## Recorded live evidence — 2026-09-11

Host acceptance tests passed: `systemd --user` units were linked and
`local-ai.target` was enabled for login. The dependency-aware startup
transaction reached all readiness endpoints, then `tests/smoke.sh` passed:
inference, embeddings, GPU visibility, tool isolation, corrected read-only
workspace/data allowlist checks, Codex bridge workflow, SearXNG, web-fetch
policy, and Docling gate. This is host acceptance evidence, not CI evidence;
browser-owned acceptance remains outside it.

Post-remediation verification on this host also passed: every SIF-backed unit
was restarted directly through systemd and passed its receipt `ExecStartPre`;
Docling gate and tool bridge started with locked, no-sync uv environments; and
the full smoke suite passed after those restarts. Model download re-runs
verified the existing checksummed artifacts without downloading them again.

| Requirement | Implementation evidence | Required live evidence |
| --- | --- | --- |
| Apptainer GPU passthrough | `apptainer --nv` configuration | CUDA OCI `nvidia-smi` test |
| Local streaming Qwen chat | Apptainer llama-server scripts, native Open WebUI and `/v1` wiring | `tests/smoke.sh` steps 1–5 |
| GPU use, VRAM, tok/s, TTFT | `--nv` inference configuration, benchmark harness | `benchmark.sh 32768`, then record result |
| 64k practical context | Context environment and long-prompt benchmark | `benchmark.sh 65536`, stability runs |
| Persistent chats | `data/open-webui` bind mount | Manual test 1 in `TESTING.md` |
| Fast / Think / Research | `config/open-webui/model-profiles.md` | Create models in first-admin UI, manual test 5 |
| Vision | Explicitly unsupported by selected text GGUF | Choose and test a matching multimodal model/projector before claiming it |
| PDF/document RAG | Open WebUI RAG + local Qwen embedding service | Deterministic test in `RAG.md` |
| Default web search | Built-in Open WebUI native tools + loopback SearXNG | Admin UI profile settings; grounded answer with citations |
| Public-web SSRF protection | Local/private fetches disabled, redirect guard and filter configured | `tests/web-fetch-isolation.sh` passed; browser/API rejection probes remain recommended |
| Docling GPU extraction | GPU Docling SIF + serialized loopback gate | Scanned Japanese/English and table PDF Knowledge tests |
| Explicit long-term memory | Disabled Open WebUI memories + owner-managed YAML | `memory.sh` inspection/edit/delete/backup exercise |
| Sandboxed Python/shell/git | Separate immutable Apptainer tool SIF and bridge | `tests/tool-isolation.sh` and OpenAPI manual test |
| Codex-style coding workflow | Qwen Codex native adapter, writable bridge, and profile approval protocol | `tests/tool-bridge-codex.sh`; browser plan/approval/edit/test/commit exercise |
| Restricted workspace binding | Tool bridge mounts `/workspace` read-only by default, or read-write only when configured | `tests/tool-bridge-allowlist.sh` verifies mount mode and denied writes |
| Optional data binding | Configured host directory is mounted only as `/data:ro` | `tests/tool-bridge-allowlist.sh` verifies mount mode and denied writes |
| Hidden-path masking | Configured sensitive children are masked while ordinary adjacent files remain visible | `tests/tool-bridge-allowlist.sh` |
| Home and secret-path isolation | `--cleanenv --containall --no-home` tool invocation | `tests/tool-isolation.sh` |
| Tool-container network behavior | `--net --network none` is used when the host probe succeeds | Passed here: `tests/tool-isolation.sh` blocked DNS/egress; otherwise `NETWORK ISOLATION: NOT GUARANTEED` |
| Backend replacement | OpenAI-compatible endpoint variables | Manual test 6 in `TESTING.md` |
| Predictable lifecycle | start/stop/log/update/doctor scripts | Native start/stop/restart cycle |

Current state: recorded host acceptance checks above have passed on the stated
dates. CI validates CPU-only configuration, adapter, Python, and shell checks;
it does not run GPU/Apptainer acceptance or benchmarks. The browser-owned
acceptance items remain intentionally unchecked until the owner completes first
login and the listed deterministic UI tests.
