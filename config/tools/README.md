# Tool sandbox policy

`tool-sandbox.sif` is a separate immutable Apptainer image with Python, Git,
and bash. Its execution contract is `--cleanenv --containall --no-home
--writable-tmpfs`, plus an explicit `/workspace` bind and optional `/data:ro`
bind. Read calls mount `/workspace:ro`; write calls mount it `:rw` only when
enabled. Its temporary root filesystem can be modified inside the process but
no modifications reach the host except under a permitted writable workspace.

The Qwen Codex adapter can run unrestricted commands inside `/workspace` when
the owner sets `TOOL_WRITE_MODE=read_write`; this includes destructive workspace
operations and project-local package commands. It cannot access paths outside
the explicit bind. The restricted review adapter always uses a read-only mount.
Every call is auditable. Test the actual isolation with
`./tests/tool-isolation.sh` before enabling the Open WebUI tool.
