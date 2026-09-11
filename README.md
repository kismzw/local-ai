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
./scripts/install-uv.sh
./scripts/setup.sh
./scripts/pull-images.sh
./scripts/download-model.sh
./scripts/download-docling-models.sh
./scripts/start.sh
```

Open `http://${OPEN_WEBUI_BIND}:${OPEN_WEBUI_PORT}` using your `.env` values and create the one permitted initial account; it
becomes the admin. Later signups are disabled. The application runs in offline
mode after setup has synchronized the locked Python dependencies and image/model
downloads complete.
`./scripts/stop.sh`, `./scripts/logs.sh`, and `./scripts/update.sh` manage the
stack. `setup.sh` enables a user systemd target so the stack starts at login;
it does not enable lingering after logout. Model identity is checksum verified
in `config/models.toml`, and normal updates refresh only digest-locked SIFs.
Use `scripts/update-lock.py` only after deliberately selecting and validating a
new upstream digest.
Existing SIFs created before receipt tracking require one explicit migration:
`./scripts/pull-images.sh --adopt-existing`. Normal pulls then fail closed if a
receipt is missing or does not match the local artifact.

## Everyday use

Create the Fast, Think, Research, and Codex presets once using
`config/open-webui/model-profiles.md`. Enable Qwen Codex only after configuring
the workspace and write mode; it follows a plan-then-approval workflow before it edits files; it
can test and commit successful work in that workspace. Review its
[containment and command policy](config/open-webui/tool-bridge.md). Upload
documents into a Knowledge collection for RAG. Explicit long-term memory is
managed with
`./scripts/memory.sh`; it is never silently written by the model.

## Operations

- Open Local AI and its dedicated Firefox window: `./local-ai open`
- Close that Firefox window and stop all Local AI services: `./local-ai close`
- Install/enable the login-time systemd user target: `./local-ai install`
- Install GNOME app-menu/Desktop launchers: `./local-ai install-launcher`
- If Firefox is not auto-detected, set its executable path as `FIREFOX_BIN` in `.env`.
- Preflight/live diagnostics: `./scripts/doctor.sh`
- Smoke test: `./tests/smoke.sh`
- 32k/64k benchmarks: `./scripts/benchmark.sh 32768` and `./scripts/benchmark.sh 65536`
- Web search: SearXNG runs locally at `127.0.0.1:8082`; select lowercase
  `searxng` and leave the web loader at **Default** (the safe-web loader) in
  the one-time Admin UI setup in `config/open-webui/web-search.md`.
- Back up: stop services and copy `data/open-webui`, `data/memory`, `.env`, `images/*.sif`, and `images/receipts.toml` to encrypted storage.

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md),
[RAG](docs/RAG.md), [memory](docs/MEMORY.md), [tools](docs/TOOLS.md), and
[troubleshooting](docs/TROUBLESHOOTING.md) for the operational detail.
