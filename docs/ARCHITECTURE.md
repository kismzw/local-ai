# Architecture

```text
Browser (127.0.0.1:3000)
  -> Open WebUI native user-space process (persistent conversations, RAG)
       -> localhost llama.cpp /v1 in Apptainer --nv (Qwen3.8-27B Q4_K_M)
       -> localhost llama.cpp embeddings in Apptainer --nv (Qwen3 Embedding)
       -> localhost SearXNG in Apptainer (public-web search only)
       -> localhost Docling gate -> Docling CUDA in Apptainer (document extraction)
       -> localhost tool bridge
            -> separate Apptainer SIF --containall + explicit /workspace bind
               + optional explicit /data:ro bind + secret-file masking
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

Web search is a separate, deliberate egress path: SearXNG queries public search
engines and Open WebUI fetches selected public pages. Both listeners remain on
loopback. The Python/Git/shell tool SIF remains on `--net --network none` and
never performs search or page fetching. Docling shares the GPU with inference
through a best-effort single-job gate; it checks llama.cpp's authenticated
`/slots` state (with metrics fallback) for idle inference but does not provide
strict GPU mutual exclusion.
