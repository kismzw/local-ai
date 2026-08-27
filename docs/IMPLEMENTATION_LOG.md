# Implementation log

- 2026-08-21: Audited the host. Ubuntu 24.04.3, RTX 5090 (32 GB), driver 580.95, 3.5 TB free; Apptainer 1.3.4 with setuid enabled and unprivileged user namespaces available.
- 2026-08-21: Verified `apptainer exec --nv docker://nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi`; the RTX 5090 is visible inside an OCI-derived SIF.
- 2026-08-21: Cached the official `ggml-org/llama.cpp:server-cuda` SIF. Corrected its Apptainer invocation to use `/app/llama-server` and `LD_LIBRARY_PATH=/app`; llama.cpp lists CUDA0 RTX 5090 successfully.
- 2026-08-21: Installed uv and Python 3.11 in user space only; built the separate immutable Python/Git/bash tool SIF. Filesystem and `--net --network none` egress-isolation tests passed.
- 2026-08-21: Downloaded and SHA-256 verified `Qwen3.8-27B-Q4_K_M.gguf`; started the CUDA llama.cpp SIF on loopback with all layers offloaded. `/v1/models`, normal chat, SSE streaming, GPU visibility, and metrics all passed.
- 2026-08-21: Started Open WebUI natively with user-space uv/Python 3.11 and its data under `data/open-webui`; its loopback health check and the separate local Qwen embedding endpoint passed.
- 2026-08-21: Recorded 32k and 64k benchmark results in `benchmarks/results/`: 65.7 tok/s / 1.14 s short TTFT at 32k, and 65.2 tok/s / 1.05 s short TTFT in the 64k configuration. Long prompts reached 23.0k and 45.9k tokens respectively.
- 2026-08-21: Re-ran `doctor.sh` and the full smoke suite after making the real-home isolation check dynamic. All automated checks pass; browser-owned acceptance tests remain listed in `docs/ACCEPTANCE.md`.
- 2026-08-26: Added self-hosted SearXNG as a loopback-only Apptainer SIF. Its JSON search endpoint was verified against a public query; the SIF identity is recorded in `config/apptainer/images.lock`.
- 2026-08-26: Added the official CUDA Docling Serve SIF, persisted its local extraction artifacts, and placed a serialized, authenticated loopback gate in front of it. The shipped `docling-serve` is v1.12.0 and bundles Docling v2.72.0; an authenticated PDF conversion through the gate passed.
- 2026-08-26: Validated SearXNG JSON search, the pinned Open WebUI SSRF policy, Docling extraction through the Open WebUI `X-Api-Key` path, and active-slot detection for best-effort inference priority.
- 2026-08-26: Added the Qwen Codex native workspace adapter and enabled contained writable workspace execution. The live bridge test verified authentication, output capping/auditing, per-repository Git commits, identity failure handling, and continued filesystem/network isolation.
