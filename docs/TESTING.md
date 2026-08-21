# Testing

Run `./tests/smoke.sh` after the native services are healthy. It validates model discovery,
non-streaming and SSE chat, GPU visibility, UI health, embeddings, and core
sandbox execution/isolation. `./scripts/doctor.sh` gives a broader operator
check. Track results in `docs/ACCEPTANCE.md` rather than inferring them from
configuration alone.

Manual deterministic checks:

1. Create a user, chat, restart with `./scripts/stop.sh && ./scripts/start.sh`, and confirm the chat remains.
2. Follow `docs/RAG.md` and confirm the validation code is retrieved only with its collection enabled.
3. Enable the bridge, add its OpenAPI tool, and ask Qwen Research to run `python -c "print(2 + 2)"`; confirm `4`.
4. Run `./tests/tool-isolation.sh`; it must prove workspace write capability and home/SSH/host-path isolation. Record whether unprivileged network namespaces work.
5. Verify Qwen Fast/Think/Research are present after following `config/open-webui/model-profiles.md`.
6. Change only endpoint/model variables in a copy of `.env` to prove backend replacement does not require UI changes.
