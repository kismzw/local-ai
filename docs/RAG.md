# RAG

After login, upload a PDF, Markdown, text, source, or DOCX file in Open WebUI,
then add it to a Knowledge collection. Enable that collection in a Qwen Research
chat. The collection and vector data persist under `data/open-webui`.

Deterministic validation: create a text file containing `The local validation
code is RAG-5090-AURORA.` Upload it to a new collection, then ask: "What is the
local validation code? Answer only from the collection." A grounded answer is
`RAG-5090-AURORA`; delete the collection afterwards.

Document parsing is Open WebUI's built-in pipeline. Docling is deferred rather
than duplicating parsers; add it only if PDF extraction quality is measured as
insufficient. Qdrant can later replace the local vector layer without changing
the OpenAI inference boundary.
