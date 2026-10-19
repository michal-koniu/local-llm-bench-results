# Parallel agents

How fast is each agent when **several agents share one model** at the same time? This happens when one
llama-server instance serves several agents through its slots (`--parallel N`) with continuous batching, so
it decodes all of them in one batch.

Measured on 2026-10-11 on the reference rig ([hardware.md](hardware.md)) with llama.cpp build 265 (`680a036`)
and the models' own serving flags ([serving/llama-swap.yaml](serving/llama-swap.yaml)). Each agent sends a
**different** prompt (nothing shared), and all agents start at the same moment. One "turn" means reading the
context and then writing 512 tokens.

> **Update 2026-10-19.** The DeepSeek tables below describe the configuration of 2026-10-11 (4 slots, layer split, no draft). DeepSeek is now served with a speculative-decoding
> draft and tensor split on 2 slots; one agent runs at ~50 tok/s and two agents at ~63 tok/s combined. See [SPEC-DECODING.md](SPEC-DECODING.md).

## DeepSeek-V4-Flash-0731 (UD-IQ3_XXS, 4 GPUs, served with `--parallel 4`)

**Typical agent turn: 4,096 tokens of context in, 512 out**

| Agents at once | Decode per agent | Decode total | Prompt read, total | One turn takes | Each agent vs alone |
|---:|---:|---:|---:|---:|---:|
| 1 | 22.6 tok/s | 22.6 tok/s | 1,186 tok/s | 26 s | – |
| 2 | 19.0 tok/s | 38.1 tok/s | 1,501 tok/s | 32 s | −16% |
| 3 | 16.9 tok/s | 50.6 tok/s | 1,633 tok/s | 38 s | −25% |
| 4 | 13.6 tok/s | 54.3 tok/s | 1,694 tok/s | 47 s | −40% |

**Long document: 16,384 tokens of context in, 512 out**

| Agents at once | Decode per agent | Decode total | Prompt read, total | One turn takes | Each agent vs alone |
|---:|---:|---:|---:|---:|---:|
| 1 | 21.7 tok/s | 21.7 tok/s | 1,330 tok/s | 36 s | – |
| 2 | 17.7 tok/s | 35.4 tok/s | 1,425 tok/s | 52 s | −18% |
| 3 | 15.0 tok/s | 45.1 tok/s | 1,461 tok/s | 68 s | −31% |
| 4 | 12.1 tok/s | 48.4 tok/s | 1,479 tok/s | 87 s | −44% |

**Live check through llama-swap** (`--parallel 4`, 4 slots × 131,072 tokens of context): 4 requests sent at
once, 256 tokens each, ran at 14.1 tok/s per agent and 54.5 tok/s combined, matching the table. VRAM use was
81–88% per GPU.

## gpt-oss-20b (MXFP4, 1 GPU, llama-server's default of 4 slots)

**Typical agent turn: 4,096 tokens of context in, 512 out**

| Agents at once | Decode per agent | Decode total | Prompt read, total | One turn takes | Each agent vs alone |
|---:|---:|---:|---:|---:|---:|
| 1 | 141.3 tok/s | 141.3 tok/s | 6,530 tok/s | 4.3 s | – |
| 2 | 109.9 tok/s | 219.9 tok/s | 6,492 tok/s | 5.9 s | −22% |
| 3 | 93.3 tok/s | 279.8 tok/s | 6,529 tok/s | 7.4 s | −34% |
| 4 | 81.3 tok/s | 325.1 tok/s | 6,519 tok/s | 8.8 s | −42% |

**Long document: 16,384 tokens of context in, 512 out**

| Agents at once | Decode per agent | Decode total | Prompt read, total | One turn takes | Each agent vs alone |
|---:|---:|---:|---:|---:|---:|
| 1 | 128.8 tok/s | 128.8 tok/s | 5,336 tok/s | 7.0 s | – |
| 2 | 96.8 tok/s | 193.6 tok/s | 5,320 tok/s | 11.4 s | −25% |
| 3 | 79.6 tok/s | 238.8 tok/s | 5,300 tok/s | 15.7 s | −38% |
| 4 | 67.4 tok/s | 269.6 tok/s | 5,280 tok/s | 20.0 s | −48% |

## How to read it

- **Decode per agent** is the speed each agent sees while all of them are writing at once. **Decode total** is
  the sum of all agents: the work the machine gets done.
- **These are worst-case per-agent numbers.** Real agents spend part of each turn waiting for tool results, so
  they rarely all decode at the same moment.
- **DeepSeek: 3 agents is the sweet spot.** Each keeps 75% of its solo speed and the machine does 2.2× the work.
  At 4 agents the total barely grows (54 vs 51 tok/s) while each agent drops to 60%. Beyond 4 is not worth it.
  The model is a mixture of experts, and different agents use different experts, so batching helps less than
  with a dense model.
- **gpt-oss-20b keeps scaling** (2.3× the total at 4 agents) and stays fast per agent (81 tok/s).
- **Reading long prompts is shared, not parallel.** Total prompt speed hardly rises with more agents, so 4 agents
  that each start with 16k tokens of context wait 44 s (DeepSeek) before the first token. With slots, each agent
  keeps its own prompt cache, so later turns re-read only the new part of the conversation.
- **Single-agent speed is unchanged** by having slots. The 1-agent rows are close to the throughput runs in
  [RESULTS.md](RESULTS.md) and a little lower, because each agent here already carries 4k–16k tokens of context.

## Reproduce

```bash
# DeepSeek-V4-Flash-0731, 4 GPUs (the serving flags of serving/llama-swap.yaml)
HIP_VISIBLE_DEVICES=0,1,2,3 llama-batched-bench \
  -m DeepSeek-V4-Flash-0731-UD-IQ3_XXS-00001-of-00004.gguf -ngl 999 -sm layer -ts 0.97,1,0.92,1.11 \
  -fa on -ub 1024 -b 2048 -c 69632 --load-mode dio -npp 4096,16384 -ntg 512 -npl 1,2,3,4

# gpt-oss-20b, 1 GPU
HIP_VISIBLE_DEVICES=0 llama-batched-bench \
  -m gpt-oss-20b-MXFP4.gguf -ngl 999 -fa on -ub 2048 -b 2048 -c 69632 --load-mode dio \
  -npp 4096,16384 -ntg 512 -npl 1,2,3,4
```

`-npl` sets the number of agents and `-npp`/`-ntg` the tokens read and written per agent; prompts are not
shared between agents (no `-pps`). The tables above map the tool's columns as follows: per-agent decode =
`S_TG / B`, total decode = `S_TG`, prompt read = `S_PP`, one turn = `T`.

<details><summary>Raw llama-batched-bench output</summary>

DeepSeek-V4-Flash-0731:

```
|    PP |     TG |    B |   N_KV |   T_PP s | S_PP t/s |   T_TG s | S_TG t/s |      T s |    S t/s |
|-------|--------|------|--------|----------|----------|----------|----------|----------|----------|
|  4096 |    512 |    1 |   4608 |    3.453 |  1186.14 |   22.674 |    22.58 |   26.127 |   176.37 |
|  4096 |    512 |    2 |   9216 |    5.457 |  1501.15 |   26.907 |    38.06 |   32.364 |   284.76 |
|  4096 |    512 |    3 |  13824 |    7.523 |  1633.38 |   30.358 |    50.60 |   37.881 |   364.93 |
|  4096 |    512 |    4 |  18432 |    9.670 |  1694.23 |   37.715 |    54.30 |   47.385 |   388.98 |
| 16384 |    512 |    1 |  16896 |   12.321 |  1329.81 |   23.614 |    21.68 |   35.935 |   470.19 |
| 16384 |    512 |    2 |  33792 |   23.002 |  1424.55 |   28.917 |    35.41 |   51.920 |   650.85 |
| 16384 |    512 |    3 |  50688 |   33.649 |  1460.73 |   34.055 |    45.10 |   67.703 |   748.68 |
| 16384 |    512 |    4 |  67584 |   44.320 |  1478.71 |   42.343 |    48.37 |   86.663 |   779.85 |
```

gpt-oss-20b:

```
|    PP |     TG |    B |   N_KV |   T_PP s | S_PP t/s |   T_TG s | S_TG t/s |      T s |    S t/s |
|-------|--------|------|--------|----------|----------|----------|----------|----------|----------|
|  4096 |    512 |    1 |   4608 |    0.627 |  6530.14 |    3.625 |   141.25 |    4.252 |  1083.71 |
|  4096 |    512 |    2 |   9216 |    1.262 |  6492.13 |    4.657 |   219.89 |    5.919 |  1557.10 |
|  4096 |    512 |    3 |  13824 |    1.882 |  6529.40 |    5.489 |   279.83 |    7.371 |  1875.45 |
|  4096 |    512 |    4 |  18432 |    2.513 |  6519.22 |    6.300 |   325.06 |    8.814 |  2091.33 |
| 16384 |    512 |    1 |  16896 |    3.070 |  5336.46 |    3.976 |   128.76 |    7.047 |  2397.73 |
| 16384 |    512 |    2 |  33792 |    6.159 |  5320.46 |    5.289 |   193.60 |   11.448 |  2951.72 |
| 16384 |    512 |    3 |  50688 |    9.274 |  5299.75 |    6.433 |   238.78 |   15.707 |  3227.06 |
| 16384 |    512 |    4 |  67584 |   12.413 |  5279.60 |    7.597 |   269.58 |   20.010 |  3377.50 |
```

</details>
