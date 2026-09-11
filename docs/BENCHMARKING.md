# Benchmarking

Start the Apptainer inference service, then run `./scripts/benchmark.sh 32768`, inspect its timestamped Markdown result,
then repeat with `./scripts/benchmark.sh 65536`. The script recreates the
inference container at that context size, captures GPU snapshots, transport
TTFT, llama.cpp Prometheus prompt/decode throughput, short generation, and a
long prompt requesting about 70% of the configured context. The report records
the requested approximation; tokenizer-derived prompt counts are not claimed.
After a 64k run, it restores services with the context configured in `.env`.

Record stability during at least ten chats at each setting. Treat the highest
setting that avoids OOM, maintains acceptable latency, and leaves normal desktop
GPU headroom as the practical maximum. Do not treat the model's advertised
maximum context as a hardware configuration target.
