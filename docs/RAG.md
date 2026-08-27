# RAG

After login, upload a PDF, Markdown, text, source, or DOCX file in Open WebUI,
then add it to a Knowledge collection. Enable that collection in a Qwen Research
chat. The collection and vector data persist under `data/open-webui`.

Deterministic validation: create a text file containing `The local validation
code is RAG-5090-AURORA.` Upload it to a new collection, then ask: "What is the
local validation code? Answer only from the collection." A grounded answer is
`RAG-5090-AURORA`; delete the collection afterwards.

Document extraction now goes through the local Docling CUDA service, which is
fronted by `docling-gate` on loopback. It uses local EasyOCR (English/Japanese),
`dlparse_v4`, and accurate table extraction before the existing local Qwen
embedding endpoint indexes the content. The gate serializes imports and checks
llama.cpp's authenticated `/slots` state (with metrics fallback) for idle
inference. An import can therefore wait up to ten minutes while a long response
is running.

Docling model artifacts and its audit log are stored in `data/docling`; uploaded
documents, chunks, and vectors remain under `data/open-webui`. No document is
sent to a third-party OCR or image-description service. Test both a scanned
Japanese/English PDF and a table-heavy PDF before relying on a collection.
Qdrant can later replace the local vector layer without changing the OpenAI
inference boundary.
