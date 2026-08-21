# Tool sandbox policy

`tool-sandbox.sif` is a separate immutable Apptainer image with Python, Git,
and bash. Its execution contract is `--cleanenv --containall --no-home
--writable-tmpfs`, plus exactly one configured host bind:
`WORKSPACE_DIR:/workspace:rw`. Its temporary root filesystem can be modified
inside the process but no modifications reach the host except under `/workspace`.

The native localhost bridge rejects privileged, host-management, package,
destructive-Git, and recursive-delete commands. Read commands are permitted;
workspace modification requires the owner to set `TOOL_WRITE_MODE=read_write`.
Every call is auditable. Test the actual isolation with
`./tests/tool-isolation.sh` before enabling the Open WebUI tool.
