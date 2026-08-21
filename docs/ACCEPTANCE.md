# Acceptance ledger

This ledger distinguishes implementation evidence from live evidence. Do not
claim a checked item until the listed live test has run on this host.

## Recorded live evidence — 2026-08-21

| Check | Result |
| --- | --- |
| Apptainer GPU passthrough | Passed with Apptainer 1.3.4: CUDA 12.8 OCI probe and official llama.cpp SIF both see RTX 5090. |
| Inference API | Passed: localhost `/health`, `/v1/models`, chat completion, SSE stream, and `/metrics`. |
| 32k benchmark | 22.2 GiB VRAM with embedding service; TTFT 1.14 s; generation 65.7 tok/s; 23k-token prefill 3,322 tok/s / 7.33 s TTFT. [Result](../benchmarks/results/20260821-180158-32768.md) |
| 64k benchmark | Passed at 45.9k-token long prompt: 21.1 GiB VRAM without embedding server; TTFT 1.05 s; generation 65.2 tok/s; long prefill 2,905 tok/s / 16.20 s TTFT. [Result](../benchmarks/results/20260821-180229-65536.md) |
| Native Open WebUI | Passed: user-space Python 3.11 service answered `GET /health` on 127.0.0.1:3000. |
| Embeddings | Passed: Qwen3 Embedding `/v1/embeddings` returned a vector. |
| Tool filesystem isolation | Passed: Python/Git and workspace write work; real home, SSH paths, Docker socket and host paths outside the bind are absent. |
| Tool network behavior | Passed: unprivileged `--net --network none` blocked DNS/egress. `TOOL_NETWORK_MODE=isolated` is set for this host. |

Not yet browser-verified: initial-admin login, model-profile creation, chat
survival across a restart, PDF Knowledge collection grounding, and OpenAPI-tool
import. These require the owner to complete first login in the browser.

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
| Explicit long-term memory | Disabled Open WebUI memories + owner-managed YAML | `memory.sh` inspection/edit/delete/backup exercise |
| Sandboxed Python/shell/git | Separate immutable Apptainer tool SIF and bridge | `tests/tool-isolation.sh` and OpenAPI manual test |
| Restricted workspace binding | Explicit `/workspace:rw` bind only | `tests/tool-isolation.sh` |
| Home and secret-path isolation | `--cleanenv --containall --no-home` tool invocation | `tests/tool-isolation.sh` |
| Tool-container network behavior | `--net --network none` is used when the host probe succeeds | Passed here: `tests/tool-isolation.sh` blocked DNS/egress; otherwise `NETWORK ISOLATION: NOT GUARANTEED` |
| Backend replacement | OpenAI-compatible endpoint variables | Manual test 6 in `TESTING.md` |
| Predictable lifecycle | start/stop/log/update/doctor scripts | Native start/stop/restart cycle |

Current state: all automated Apptainer, inference API, embedding, benchmark,
and tool-isolation checks have passed. The browser-owned acceptance items above
remain intentionally unchecked until the owner completes first login and the
listed deterministic UI tests.
