# Speculative decoding and tensor split

How much faster does one agent get on DeepSeek-V4-Flash-0731 when the model gets a **speculative-decoding draft** and the four GPUs
split every layer (**tensor split**) instead of passing the token along as a pipeline? Measured on 2026-10-19 on the reference rig
([hardware.md](hardware.md)). The explanation of the mechanisms, the exact commands and the traps are in the course repo:
**[llm-education: speeding up generation](https://github.com/michal-koniu/llm-education/tree/main/en/speeding-up-generation)**.
This page holds the numbers.

## Summary

Single agent, mean decode speed over four kinds of task (translation, tool call, code, free prose) at temperature 0 and 1.0:

| Configuration | llama.cpp | Split | Draft | tok/s | tool call (JSON) |
|---|---|---|---|---:|---:|
| baseline | `680a036` | layer | none | **23.5** | 23.4 |
| + speculative decoding | `680a036` | layer | DSpark, 3 tokens | 35.2 | 43 |
| new build | `0ce8cd1` | layer | none | 25.2 | 24 |
| new build + draft | `0ce8cd1` | layer | DSpark, 3 tokens | 37.9 | 48–50 |
| new build | `0ce8cd1` | **tensor** | none | 29.1 | 29 |
| **deployed** | `0ce8cd1` | **tensor** | DSpark, 3 tokens | **49.2** | **54–62** |

Several agents at once on the deployed configuration (2 slots; the 4-request row queues two requests behind the first two):

| Agents | tok/s each | tok/s total |
|---:|---:|---:|
| 1 | 49.7 | 46 |
| 2 | 34.5 | **63** |
| 4 | 33 | 60 |

For comparison, the configuration of [PARALLEL.md](PARALLEL.md) (4 slots, layer split, no draft) gave 22.6 / 38 / 54 tok/s total for 1 / 2 / 4 agents.

**Costs.** Prompt reading (prefill) drops from ~960 to ~700 tok/s on a 6.2k-token prompt (layer split + draft: ~490). The deployed
configuration has **2 slots × 98,304 tokens** of context instead of 4 × 131,072: with the draft's ~4 GB per card, four slots do not fit in tensor mode.

## Conditions

| | |
|---|---|
| Hardware | 4× AMD Radeon AI PRO R9700 (32 GB), PCIe links x8/x4/x8/x4, **power cap 250 W** per GPU, ROCm 7.2.4, kernel 7.0.0-38 |
| Model | DeepSeek-V4-Flash-0731, Unsloth UD-IQ3_XXS (3.06 bpw, 4 shards, 104.2 GB) |
| Draft | DeepSeek's own DSpark head from the 0731 checkpoint (`mtp.*` tensors of shards 46–48), converted with llama.cpp's `convert_hf_to_gguf.py --dspark`; GGUF 10.9 GB, SHA-256 `860bdc80e6d4a285…` |
| llama.cpp | `680a036` (b265, 2026-09-28) and `0ce8cd1` (2026-10-19), both `GGML_HIP=ON`, `GPU_TARGETS=gfx1201`, `GGML_HIP_GRAPHS=ON`, no RCCL; the second is reported as `b1-0ce8cd1` by the server because it was built from a shallow checkout |
| Serving | llama-swap, flags in [serving/llama-swap.yaml](serving/llama-swap.yaml); `--ubatch-size 512` for configurations with a draft |
| Sampling | server defaults `temperature 1.0, top_p 1.0, top_k 0, min_p 0`; each benchmark request sets its own temperature (0 and 1.0; 0.2 for the agent tests) |
| Method | one request at a time unless stated; 300 tokens; speed from the server's own `timings.predicted_per_second`. The model's thinking tokens are counted (they are most of a short answer). Draft acceptance from `timings.draft_n_accepted / draft_n` |
| Noise | **one repetition** per cell in most tables, so differences below ~2 tok/s are noise. The baseline is stable to ±0.3 tok/s |
| Not recorded | power draw and temperatures **during** the runs (idle temperatures after the runs: 64–71 °C), PCIe error counters — unlike the [perf runs](perf/) |

## Draft length and confidence threshold (llama.cpp `680a036`, layer split, 1 slot × 131,072)

`n` = `--spec-draft-n-max`, `p-min` = `--spec-draft-p-min`. Mean tok/s over all tasks and both temperatures:

| Variant | tok/s | Note |
|---|---:|---|
| no draft | 23.5 | |
| n=5, p-min 0 | 33.2 | free prose **slower** than baseline (19–22) |
| n=5, p-min 0.5 | 34.8 | threshold rescues prose |
| n=5, p-min 0.75 | 32.1 | too conservative |
| **n=3, p-min 0** | **36.1** | best mean and best translation (34) |
| n=3, p-min 0.5 | 34.3 | |
| n=4, p-min 0 | 32.4 | |
| n=2, p-min 0 | 34.7 | most even: no task below 28 |
| n=5, p-min 0.5 + `ngram-mod` | 34.4 | n-gram lookup added nothing for ordinary text |

Per task at the deployed `n=3` (tensor split, 2 × 98,304): translation 51.9 / 43.9, tool call 62.0 / 54.0, code 58.5 / 50.9, prose 37.8 / 34.6 tok/s
(temperature 0 / 1.0); draft acceptance 0.70/0.59, 0.95/0.80, 0.82/0.73, 0.40/0.36. **The draft length was not re-tuned in tensor mode.**

## Shapes that fit in memory (`0ce8cd1`, tensor split, `--ubatch-size 512`, `n=3`)

| Slots × context | tok/s | Free VRAM, card 0 / cards 1–3 (GB, right after load) |
|---|---:|---|
| 1 × 131,072 (`ubatch 1024`) | 46.2 | 0.35 / 1.5 |
| 2 × 131,072 | 49.6 | 0.37 / 1.17 |
| **2 × 98,304 (deployed)** | **49.2** | **0.73 / 1.68** |
| 4 × 65,536 | 44.6 | 0.16 / 1.0 |
| 4 × 131,072 | — | out of memory at load |

After a realistic test run the deployed configuration had 0.82 / 1.43 GB free (card 0 / others).

## Gate results for the deployed configuration

| Test | Result |
|---|---|
| prefill, 6.2k-token prompt (two runs) | 694 and 735 tok/s (no draft: ~960; layer split + draft: 490–530) |
| text identical to the no-draft model at temperature 0 | **0 of 4** (diverges in the first tokens of the model's reasoning; final answers are correct). Layer split + draft: 2 of 4 identical |
| reload after idle unload | ~108 s (layer split: ~35 s) |

Tensor split changes the order of floating-point sums, so token-for-token agreement with the old configuration is not expected; so quality needs its own measurement, which has not been done yet (see Quality).

## Quality

**Not measured after the change.** Before (2026-10-10, llama.cpp `680a036`, layer split, no draft, hard suite, k = 3):
[quality/20261010-221652-deepseek-v4-flash-0731-recommended-hard](quality/20261010-221652-deepseek-v4-flash-0731-recommended-hard/report.md) — PL 92, EN 93.
I started the same suite on the deployed configuration and **stopped it after 11 of 120 samples**: a full run takes several hours (about 2 minutes per sample on this rig,
even at the new speed), and 11 samples support no conclusion, so they are not published here.

What is known: speculative decoding does not change the output distribution by construction; tensor split reorders floating-point sums, so temperature-0 text is no longer identical to the old
configuration's (0 of 4 prompts identical), and the answers that were read were correct. That is not a quality measurement. To measure it:
`python3 -m qbench run --model deepseek-v4-flash-0731 --suite hard --k 3` ([local-llm-quality-bench](https://github.com/michal-koniu/local-llm-quality-bench); the run manifest records the
full server command line, so the configuration is reproducible) and compare with the report above.

## Things that failed

- **Uneven `--tensor-split` in tensor mode hangs at load** (`0.85,1,1,1`): no response for 300 s. Equal split loads in ~108 s. Found by running the server directly with one change at a time.
- **4 slots × 131,072 do not fit**: `cudaMalloc failed: out of memory` for a ~2.75 GB allocation on card 0.
- `--fit` (auto-fit to free memory) is not implemented for tensor mode, and the KV cache must stay unquantised (`-ctk f16 -ctv f16`).
- The log reports `AllReduce init failed (n_devices != 2?); falling back to meta-backend butterfly`: with four cards a generic reduction path is used. RCCL and peer-to-peer access were **not tested**.

## Data

Raw per-request results (JSON) and logs of every run behind these tables: [spec-decoding/data/](spec-decoding/data/README.md).
Scripts: [local-llm-perf-bench/server-bench](https://github.com/michal-koniu/local-llm-perf-bench/tree/main/server-bench).
