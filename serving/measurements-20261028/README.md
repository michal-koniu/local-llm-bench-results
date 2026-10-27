# Measurements 2026-10-28

All with vendor sampling, measured from the client (`local-llm-perf-bench/server-bench/bench_stream.py`), through
llama-swap with the final config (`../llama-swap.yaml`). Code context: llama.cpp `tools/server/server-context.cpp`
(first 52,000 characters, ~14k tokens). rep 0 = first request after start (warm-up), rep 1 = warm.

| File | What |
|---|---|
| `stream-all.txt` | every model of the final lineup, all concurrency levels (12-agent run of `-x4` hit the default `concurrencyLimit` 10 → 2 of 12 requests got HTTP 429) |
| `stream-all-c12-rerun.txt`, `stream-qwen3.6-35b-a3b-x4-c12.json` | `-x4` at 12 agents after `concurrencyLimit: 20` |
| `stream-<model>.json` | per-model raw results |

## Tuning sweeps behind the config (same prompts, server started per variant)

**llama.cpp speculative decoding, draft length** (tok/s, chat / code16k, temp = vendor):

| Model | Variant | chat | code16k |
|---|---|---:|---:|
| Qwen3.8-Flash-Next (4 GPU, ROCm) | MTP n-max 4 (old) | 41–43 | 41–43 |
| | **MTP n-max 2** | **49–50** | 44–45 |
| | MTP 3, p-min 0.3 | 48–50 | 41–49 |
| | MTP 8, p-min 0.6 | 39–41 | 35–38 |
| | MTP 4 + ngram 16 | 41–45 | 39–41 |
| Gemma 4 26B-A4B (1 GPU, Vulkan) | none | 99 | 88 |
| | MTP 3 + ngram (old) | 145–151 | 163–164 |
| | MTP 2 / 3 / 5 | 142–145 / 141–149 / 131–137 | 151 / 159–163 / 183–188 |
| | **MTP 4 + ngram** | 136–137 | 177 |
| Qwen3.6-35B-A3B (1 GPU, Vulkan) | **ngram-mod** | 106–108 | 101–114 |
| | embedded MTP n 2 / 3 / 4 (unsloth MTP GGUF) | 40–41 / 36–40 / 32–34 | 36–37 / 34–37 / 36 |
| Bielik 11B (1 GPU) | ROCm / ROCm+ngram / **Vulkan** / Vulkan+ngram | 45 / 45 / **47–48** / 48 | 36 / 36 / **37** / 37 |
| DeepSeek-V4-Flash (4 GPU) | DSpark 2 / **3** / 5 | 41 / 41–43 / 43 | 36–37 / 39–52 / 34–39 |

**vLLM Radiance fork** (Qwen3.6-35B-A3B FP8; Qwen3.8-27B MXFP4):

| Setup | 1 agent | 8 agents (each) | 12 agents (each) |
|---|---:|---:|---:|
| Qwen3.6 TP2, KV fp8 (uncalibrated) | 109–140 | 80–87 | – |
| **Qwen3.6 TP2, KV bf16** | 139–146 | 85–88 | – |
| **Qwen3.6 TP4, KV bf16, 16 seqs** | 125–255 | 80–101 | 74–83 |
| Qwen3.6 DP2 × TP2 | crashed under load | | |
| Qwen3.8-27B TP1, 64k ctx | 78–96 | 63–89 (4 agents) | – |
| Qwen3.8-27B TP2, KV fp8 | 118–188 | 66–73 | – |
| Qwen3.8-27B TP2, KV bf16 | 123–167 | 68–74 | – |

**radiance, Qwen3.8-Flash-Next** (2 GPU unless noted):

| Setup | chat 1 | code16k 1 | 4 agents (each) | RAM (container) |
|---|---:|---:|---:|---:|
| author: `--tp-wire wht6`, KV fp8, pool 12 GB | 78–103 | 108–134 | 85–89 | – |
| exact wire, KV bf16, pool 12 GB, n-gram auto (→ disk) | 82–144 | 88–160 | 81–93 | 38.5 GB |
| **exact wire, KV bf16, pool 8 GB, n-gram disk** | 119–151 | 128–129 | 82–92 | **30.5 GB** |
| TP4, exact, bf16, pool 12 GB | – | – | – | **53 GB → swapping (aborted)** |
