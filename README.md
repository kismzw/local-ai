# Local AI

A local-first ChatGPT-style application: native user-space Open WebUI, CUDA
llama.cpp in Apptainer, Qwen3.8-27B Q4_K_M, Qwen embeddings for RAG, and an
Apptainer-contained Python/Git/shell tool bridge. It binds to localhost by
default and persists only application data in `data/`.

## Start

Prerequisites: Apptainer (or Singularity-compatible command), a current NVIDIA
driver, `curl`, and user-space `uv`. Docker, Docker Compose, NVIDIA Container
Toolkit, and sudo are not used. `scripts/install-uv.sh` installs uv and managed
Python 3.11 under the current user only.

```bash
git clone <your-repository-url> local-ai
cd local-ai
cp .env.example .env
./scripts/setup.sh
./scripts/install-uv.sh
./scripts/pull-images.sh
./scripts/download-model.sh
./scripts/start.sh
```

Open http://127.0.0.1:3000 and create the one permitted initial account; it
becomes the admin. Later signups are disabled. The application runs in offline
mode after image and model downloads complete.
`./scripts/stop.sh`, `./scripts/logs.sh`, and `./scripts/update.sh` manage the
stack. Open WebUI is version-pinned in `.env`; model identity is checksum
verified. The running Apptainer root filesystems are immutable SIFs. Review the
official llama.cpp OCI source before deliberately refreshing its SIF with
`./scripts/update.sh`.

## Everyday use

Create the Fast, Think, and Research presets once using
`config/open-webui/model-profiles.md`. Upload documents into a Knowledge
collection for RAG. The Apptainer tool bridge is off by default; enable it only
after reviewing [its policy](config/open-webui/tool-bridge.md). Explicit
long-term memory is managed with
`./scripts/memory.sh`; it is never silently written by the model.

## Operations

- Preflight/live diagnostics: `./scripts/doctor.sh`
- Smoke test: `./tests/smoke.sh`
- 32k/64k benchmarks: `./scripts/benchmark.sh 32768` and `./scripts/benchmark.sh 65536`
- Back up: stop services and copy `data/open-webui`, `data/memory`, `.env`, and `images/*.sif` to encrypted storage.

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md),
[RAG](docs/RAG.md), [memory](docs/MEMORY.md), [tools](docs/TOOLS.md), and
[troubleshooting](docs/TROUBLESHOOTING.md) for the operational detail.
