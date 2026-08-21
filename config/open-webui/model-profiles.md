# Logical chat profiles

Create these under **Workspace → Models** after first login. Each profile points to
`qwen3.8-27b`; profiles are Open WebUI-side presets, so changing the inference
backend later does not require UI redesign.

| Profile | Base model | Suggested parameters | Capabilities | System prompt addition |
| --- | --- | --- | --- | --- |
| Qwen Fast | `qwen3.8-27b` | temperature `0.7`, max tokens `2048` | RAG/tools off | "Answer directly and concisely. Do not use extended reasoning unless requested." |
| Qwen Think | `qwen3.8-27b` | temperature `0.5`, max tokens `4096` | RAG optional, tools off by default | "Reason carefully. State assumptions and verify calculations before concluding." |
| Qwen Research | `qwen3.8-27b` | temperature `0.3`, max tokens `4096` | RAG on; select sandbox only when requested | "Use attached or retrieved sources as evidence. Clearly distinguish retrieved evidence from general knowledge." |

Keep **Function Calling: Native** for the Research profile. Tool access remains
disabled until a terminal is selected in a chat. The Qwen GGUF controls any
model-specific thinking mode; this deployment deliberately does not pretend to
toggle an unsupported backend flag.
