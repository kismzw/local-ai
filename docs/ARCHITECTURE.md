# Architecture

```text
Browser (127.0.0.1:3000)
  -> Open WebUI native user-space process (persistent conversations, RAG)
       -> localhost llama.cpp /v1 in Apptainer --nv (Qwen3.8-27B Q4_K_M)
       -> localhost llama.cpp embeddings in Apptainer --nv (Qwen3 Embedding)
       -> localhost tool bridge
            -> separate Apptainer SIF --containall + explicit /workspace bind
```

Apptainer normally shares the host network. Both llama servers bind explicitly
to `127.0.0.1`, and no port mapping is used. Open WebUI uses only
OpenAI-compatible endpoints. Replacing llama.cpp changes
endpoint/model configuration, not the UI, data, RAG, or sandbox boundary. The
initial 32k context uses one slot to protect KV-cache room on a 32 GB GPU; test
64k with the included benchmark before adopting it.

Vision is deliberately not claimed: it requires a selected multimodal Qwen
GGUF, matching projector, and verified llama.cpp image-input support. Apptainer
containment is not a hardened VM boundary; filesystem, secret-path, write, and
network properties are tested independently.
