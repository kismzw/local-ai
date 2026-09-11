# Troubleshooting

- `apptainer: command not found`: use the managed Apptainer/Singularity installation; no Docker is needed.
- GPU passthrough fails: run `apptainer exec --nv docker://nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi`; report the error to the workstation administrator.
- Inference SIF unhealthy: verify filenames in `.env`, `images/`, `models/`, and `./scripts/logs.sh llama`.
- Context exhausted during a tool-driven review: start a fresh chat, keep tool
  commands targeted, and leave `TOOL_MAX_OUTPUT_CHARS=6000`. The default
  65536-token llama.cpp context accepts longer reviews. If GPU memory becomes
  constrained, return `MODEL_CONTEXT_SIZE` to 32768, keep
  `MODEL_PARALLELISM=1`, and leave KV cache at `q8_0`.
- Open WebUI has no model: verify the `/v1/models` check in `doctor.sh`, then inspect Admin Settings → Connections.
- RAG fails: confirm `embedding-server` is healthy and the embedding model file exists.
- Tool bridge fails: inspect `./scripts/logs.sh tool-bridge` and `data/tool-audit/tool-bridge.jsonl`.

Do not delete `data/open-webui`: it contains persistent chats, uploads and RAG data.
