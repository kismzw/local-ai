# RAG configuration

Open WebUI owns document ingestion, its persistent database, and vector storage
in `data/open-webui`. It calls `embedding-server` through the standard
OpenAI-compatible embeddings endpoint with `Qwen3-Embedding-0.6B-Q8_0.gguf`.

Open WebUI uses the local Docling gate for document extraction, including OCR and
table-aware PDF conversion, before embeddings are created. The gate serializes
work against inference and returns 503 when inference availability is unknown.

The boundary is explicit: replacing Open WebUI's built-in vector store later
with Qdrant changes this application layer only; the inference API remains
unchanged.
