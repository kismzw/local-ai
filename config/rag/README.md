# RAG configuration

Open WebUI owns document ingestion, its persistent database, and vector storage
in `data/open-webui`. It calls `embedding-server` through the standard
OpenAI-compatible embeddings endpoint with `Qwen3-Embedding-0.6B-Q8_0.gguf`.

Initial parsers are Open WebUI's built-in upload pipeline: PDF, Markdown, text,
source files, and DOCX where extraction support is available in the pinned
image. Docling is intentionally not added as a second parser until a measured
document-quality need justifies it. This avoids duplicate parsing infrastructure.

The boundary is explicit: replacing Open WebUI's built-in vector store later
with Qdrant changes this application layer only; the inference API remains
unchanged.
