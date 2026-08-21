# Models

Default primary: official `ggml-org/Qwen3.8-27B-GGUF`,
`Qwen3.8-27B-Q4_K_M.gguf` (19 GB, SHA-256 verified by the download script).
It is launched with `apptainer exec --nv`; all layers are requested on GPU and
CPU offload is not configured. The official `ggml-org` CUDA server OCI image is
cached as an immutable SIF under `images/`.

Embeddings: `Qwen/Qwen3-Embedding-0.6B-GGUF`, `Q8_0`, with llama.cpp embedding
mode and `last` pooling. Downloads are always explicit, never a startup side
effect. To replace a backend, preserve OpenAI-compatible `/v1` and change .env.
