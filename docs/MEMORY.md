# Long-term memory

Four things are intentionally separate: the current chat context, Open WebUI's
persisted conversation history, retrieved RAG knowledge, and explicit long-term
memory. Only the fourth is managed here, at `data/memory/memory.yaml`.

The model cannot silently add personal data. To create or change memory, copy
`data/memory/memory.yaml.example` to `data/memory/memory.yaml` and run
`./scripts/memory.sh edit`. Inspect with `show`, remove it with `delete`, and
create timestamped backups with `backup`. To make it retrievable, deliberately
upload that file to a dedicated, private Open WebUI Knowledge collection; omit
that collection from chats to disable retrieval. Include `data/memory` in an
encrypted backup.

`ENABLE_MEMORIES=false` and `ENABLE_MEMORY_SYSTEM_CONTEXT=false` disable Open
WebUI's automatic memory tooling in this deployment; do not enable them without
revisiting the write-approval policy.
