# Logical chat profiles

Create these under **Workspace → Models** after first login. Each profile points to
`qwen3.8-27b`; profiles are Open WebUI-side presets, so changing the inference
backend later does not require UI redesign.

| Profile | Base model | Suggested parameters | Capabilities | System prompt addition |
| --- | --- | --- | --- | --- |
| Qwen Fast | `qwen3.8-27b` | temperature `0.7`, max tokens `2048` | Web Search on; RAG/tools off | "Answer directly and concisely. Search the web only when current information would materially improve the answer; cite sources." |
| Qwen Think | `qwen3.8-27b` | temperature `0.5`, max tokens `4096` | Web Search on; RAG optional, sandbox off | "Reason carefully. State assumptions, search current claims when useful, and cite sources." |
| Qwen Research | `qwen3.8-27b` | temperature `0.3`, max tokens `4096` | Web Search and RAG on; sandbox only when requested | "Use attached, retrieved, and web sources as evidence. Clearly distinguish each from general knowledge and cite web sources." |
| Qwen Codex | `qwen3.8-27b` | temperature `0.2`, max tokens `8192` | Qwen Codex Workspace tool on; web search/RAG off by default | See the required coding-agent prompt below. |

Keep **Function Calling: Native** for every profile: Open WebUI's built-in web
tools need it even when workspace tools are otherwise disabled. Tool access
remains disabled until a terminal is selected in a chat. The Qwen GGUF controls
any model-specific thinking mode; this deployment deliberately does not pretend
to toggle an unsupported backend flag.

For Qwen Fast, Think, and Research, enable the **Web Search** capability and add
it under **Default Features**. Keep web search and RAG off for Qwen Codex unless
the task specifically needs them. Saved Admin settings override environment
defaults; see `config/open-webui/web-search.md` after first login.

## Qwen Codex setup

Create a native tool with id `qwen_codex_workspace`, paste the complete contents
of `config/open-webui/qwen-codex-tool.py`, and enable it only for the **Qwen
Codex** model. Add this system prompt to that model:

> You are a careful local coding agent. For every implementation request, first
> inspect the workspace using `inspect_workspace`, then state a concise plan and
> wait for the user's explicit approval before calling `modify_workspace`. After
> approval, implement the plan, run relevant checks, and report changed files,
> validation results, and commit hashes. Commit each changed Git repository
> separately only after checks pass. Use an existing repository-local Git
> identity; if absent, ask the user for name and email and use `git -c` options
> for that commit without persisting them. If checks fail, do not commit: retain
> the changes and report the failure. Keep all commands inside `/workspace`.

This approval protocol is model-mediated: Open WebUI tools cannot independently
verify that an earlier chat message was written by the user.
