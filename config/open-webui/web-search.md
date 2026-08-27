# Enable default Web Search

After first administrator login, open **Settings → Admin → Tools → Web Search**
and select the lowercase `searxng` provider, then enter
`http://127.0.0.1:8082/search?q=<query>`, five results, one concurrent search,
and the **Default** web loader. In Open WebUI 0.11.0, Default is its built-in
safe-web loader; `safe_web` is not separately listed in the dropdown. Set two
concurrent fetches, a 20-second fetch
timeout, and a 40,000-character page cap. Keep local-web fetch disabled,
TLS verification enabled, and redirect following disabled. The fetch filter
must include `!localhost`, `!127.0.0.1`, and `!::1` in addition to Open WebUI's
private-address defaults.

For each Qwen profile under **Workspace → Models**, set Function Calling to
**Native**, enable the **Web Search** capability, and add **Web Search** to
Default Features. This makes search available in each new chat; it does not
force every message to leave the machine. The model should cite pages it reads.

For the administrator account that uses the UI, also open **Settings →
Interface** (not Admin Panel) and set **Web Search in Chat** to **Always**.
Open WebUI 0.11.0 otherwise sends `web_search: false` for some new chats even
when a model profile lists Web Search under Default Features. Create a new chat
after changing this setting. “Always” means the web tool is available by
default; the model still chooses whether to call it.

The SearXNG and Docling endpoints are loopback-only. Do not expose their ports
or add the Python/Git/shell sandbox as a search tool.

## Document extraction

In **Settings → Admin → Documents**, select **Docling** and set the server URL
to `http://127.0.0.1:5001`. Set its API key to the value of
`DOCLING_GATE_API_KEY` from `.env`, and use these parameters:

```json
{"do_ocr":true,"ocr_engine":"easyocr","ocr_lang":["en","ja"],"pdf_backend":"dlparse_v4","table_mode":"accurate","pipeline":"standard"}
```

Open WebUI 0.11.0 supplies this key as `X-Api-Key`; the local gate accepts that
documented header (and a bearer key for operational probes). Do not edit
`data/open-webui/webui.db`: Admin-saved ConfigVars override environment seeds.
