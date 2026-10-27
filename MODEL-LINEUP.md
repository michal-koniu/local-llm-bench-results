# Model lineup and serving guide — 4× Radeon AI PRO R9700

**State as of 2026-10-27.** Which model to use for what, how fast each one really is on this rig, why it is
configured the way it is, and how to point OpenClaw or any other harness at it.

Everything is served by **llama-swap on port 8080** (OpenAI-compatible): `http://192.168.0.39:8080/v1`.
Pick a model by its name in the `model` field; llama-swap loads it on demand and unloads whatever was in the way.

---

## 1. The lineup at a glance

| Rank (intelligence) | Model (`model` name) | Intelligence evidence | Speed, 1 agent (measured) | Several agents | GPUs | Use it for |
|---:|---|---|---|---|---|---|
| 1 | **`qwen3.8-flash-next`** | Qwen-reported SWE-bench Pro **62.5**, DeepSWE 58.7 — above DeepSeek-V4-Flash-0731 (56.0) in the same table | **~70 tok/s** (tool calls 78–97, prose ~45) | 2 slots, but 2 at once = ~38 tok/s each (~69 total): no gain over one | 4 | The hardest single-chat tasks: architecture, long reasoning, difficult code |
| 2 | **`deepseek-v4-flash-0731`** | **Our hard suite: 92 PL / 93 EN** (agents 97/97). Terminal-Bench 2.1 82.7 (DeepSeek) | ~50 tok/s | 2 slots, ~63 tok/s total | 4 | Second opinion; **longest context** (196k served, 512k in `-nospec`) |
| 3 | **`qwen3.6-35b-a3b`** / **`qwen3.6-35b-a3b-x4`** | Artificial Analysis index **18** (gpt-oss-120b: 12); SWE-bench Verified 73.4, Terminal-Bench 51.5 (Qwen) | **122–130 tok/s** | pool: 4 agents × ~200, **12 agents × ~107 tok/s** | 1 / 4 | **Agentic work, many agents in parallel** (OpenClaw, coding harnesses) |
| 4 | **`gemma-4-26b-a4b`** | Artificial Analysis index **17**; different model family from Qwen | **~170 tok/s** (tool calls 182–191) | 2 slots: ~366 tok/s total on short prompts | 1 | Fastest agent; second-family opinion; runs **together with** `qwen3.6-35b-a3b` |
| — | `bielik-11b` | Polish specialist (11B dense) | ~45 tok/s | — | 1 | Polish-language text only; weak at tool use |
| — | `deepseek-v4-flash-0731-nospec` | same as #2 | ~24 tok/s, but prompt reading ~2× faster | 4 slots × 131k | 4 | Huge prompts with short answers |

**How to read "intelligence".** Only DeepSeek has been measured with our own hard suite
([local-llm-quality-bench](https://github.com/michal-koniu/local-llm-quality-bench)). The other three ranks come
from vendor tables and Artificial Analysis — consistent with each other, but not yet confirmed on our tasks.
Run the hard suite on `qwen3.8-flash-next`, `qwen3.6-35b-a3b` and `gemma-4-26b-a4b` when you have a free evening
to turn ranks 1, 3 and 4 into measured numbers.

**Speeds** are llama-server's own counters (`timings.predicted_per_second`) through llama-swap with the exact
serving flags, from `server-bench/bench_spec.py` (one agent, four kinds of task, temperature 0 and 1) and
`bench_conc.py` (several agents). Raw files: [`serving/measurements-20261027/`](serving/measurements-20261027/).

### Quick choice

- **"I want the best possible answer and I'll wait."** → `qwen3.8-flash-next` (or `smartest`).
- **"One coding agent / OpenClaw, fast."** → `gemma-4-26b-a4b` (~170 tok/s) or `qwen3.6-35b-a3b` (~125 tok/s, slightly smarter).
- **"8–12 agents at once."** → `qwen3.6-35b-a3b-x4`.
- **"Two different agents (e.g. coder + reviewer) at the same time."** → `qwen3.6-35b-a3b` + `gemma-4-26b-a4b`;
  both stay loaded together (group `agents`, cards 1 and 2).
- **"A 300k-token document."** → `deepseek-v4-flash-0731` (or `-nospec` if the answer is short).

Only one of these can be loaded at a time: the 4-GPU models (`qwen3.8-flash-next`, both DeepSeeks,
`qwen3.6-35b-a3b-x4`) or the `agents` pair. Switching costs 10–100 s of loading.

---

## 2. Using the models from a harness

Every model speaks the OpenAI Chat Completions API, with tool calling (`tools`, `tool_calls`).

| Setting | Value |
|---|---|
| Base URL | `http://192.168.0.39:8080/v1` (from the rig itself: `http://localhost:8080/v1`) |
| API key | anything non-empty (llama-swap has no authentication) |
| Model | a name from the table above (aliases work too: `smartest`, `qwen3.6-pool`, `gemma4`, …) |
| Context window to declare | see below |

**Context to declare in the client.** Each llama-server shares its KV cache between its slots (`--kv-unified`):
one agent can use all of it when the others are short, but if every slot fills up at once there is no room left.
Declare a window that still fits when all slots are full:

| Model | Served context (shared) | Slots | Safe per-agent window to declare |
|---|---:|---:|---:|
| `qwen3.8-flash-next` | 131,072 | 2 | 65,536 (131,072 if you use one chat at a time) |
| `qwen3.6-35b-a3b` | 262,144 | 2 | 131,072 |
| `qwen3.6-35b-a3b-x4` | 196,608 per GPU | 3 per GPU (12) | 65,536 |
| `gemma-4-26b-a4b` | 131,072 | 2 | 65,536 |
| `deepseek-v4-flash-0731` | 196,608 | 2 | 98,304 |

### OpenClaw

OpenClaw talks to any OpenAI-compatible server through a custom provider. Add to `~/.openclaw/openclaw.json`
(field names as of the OpenClaw versions current in autumn 2026 — check `openclaw doctor` if your version differs):

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "rig": {
        "baseUrl": "http://192.168.0.39:8080/v1",
        "apiKey": "local",
        "api": "openai-completions",
        "models": [
          { "id": "qwen3.6-35b-a3b-x4", "name": "Qwen3.6 35B pool (12 agents)", "reasoning": true, "contextWindow": 65536,  "maxTokens": 16384 },
          { "id": "gemma-4-26b-a4b",    "name": "Gemma 4 26B (fastest)",        "reasoning": true, "contextWindow": 65536,  "maxTokens": 16384 },
          { "id": "qwen3.6-35b-a3b",    "name": "Qwen3.6 35B (1 GPU)",          "reasoning": true, "contextWindow": 131072, "maxTokens": 16384 },
          { "id": "qwen3.8-flash-next", "name": "Qwen3.8 Flash-Next (smartest)", "reasoning": true, "contextWindow": 131072, "maxTokens": 32768 }
        ]
      }
    }
  },
  "agents": { "defaults": { "model": { "primary": "rig/qwen3.6-35b-a3b-x4", "fallbacks": ["rig/gemma-4-26b-a4b"] } } }
}
```

Use the **pool** as the default when OpenClaw runs sub-agents in parallel; switch an agent to
`rig/qwen3.8-flash-next` for a single hard task (it unloads the pool for that time).

### opencode

`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "rig": {
      "name": "Local rig",
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://192.168.0.39:8080/v1" },
      "models": {
        "gemma-4-26b-a4b":    { "name": "Gemma 4 26B (fast)" },
        "qwen3.6-35b-a3b":    { "name": "Qwen3.6 35B" },
        "qwen3.8-flash-next": { "name": "Qwen3.8 Flash-Next (smartest)" }
      }
    }
  }
}
```

In opencode, pick the model with `/model` (not `/connect`).

### Anything else (Python, curl)

```python
from openai import OpenAI
c = OpenAI(base_url="http://192.168.0.39:8080/v1", api_key="local")
r = c.chat.completions.create(model="gemma-4-26b-a4b", messages=[{"role": "user", "content": "Hi"}])
```

```bash
curl -s http://192.168.0.39:8080/v1/models                 # what is configured
curl -s http://192.168.0.39:8080/running                   # what is loaded right now, with its full command line
curl -s -X POST http://192.168.0.39:8080/api/models/unload # free all GPUs
```

**Sampling.** Each model has its vendor's recommended sampling set as the server default (Qwen3.6: "thinking,
precise coding" temp 0.6 / top-p 0.95 / top-k 20; Qwen3.8: temp 1.0 / 0.95 / 20; Gemma 4: temp 1.0 / 0.95 / 64).
A client that sends its own `temperature` overrides it — many harnesses do; that is fine.

---

## 3. Why it is set up this way (what we measured)

### 3.1 What decides decode speed

Generating one token means reading every **active** weight from VRAM once. An R9700 reads ~640 GB/s, so a
model whose active weights take 3 GB can, at best, produce ~200 tokens/s. That is why the fast models here are
**Mixture-of-Experts** with few active parameters (Qwen3.6: 3B of 35B; Gemma 4: ~4B of 26B): they are large
(smart) but read little per token.

This "bandwidth ceiling" is only a ceiling. Two other things can cap speed far below it — both appear below.

### 3.2 Vulkan vs ROCm: same code, different GPU kernels

llama.cpp can drive the R9700 through **ROCm (HIP)** or **Vulkan**. Same commit, same file, one card:

| Model | ROCm decode | Vulkan decode | Prompt (4k) ROCm / Vulkan |
|---|---:|---:|---:|
| Qwen3.6-35B-A3B UD-Q5_K_XL | 86.7 | **111.3** (+28 %) | 3,589 / 3,269 (4,158 with `-ub 2048`) |
| Gemma 4 26B-A4B Q8_0 | 84.7 | **99.6** (+18 %) | 5,286 / 4,648 |
| Qwen3.8-Flash-Next (4 GPUs) | **33.2** | 27.4 | — |

Rule of thumb on RDNA4: **Vulkan for small-active MoE models on one card; ROCm for models spread over several
cards** (only ROCm has tensor split, and Vulkan's multi-GPU path was slower here). The Vulkan build lives in
`~/llama.cpp-0ce8cd1-vulkan`; the Vulkan SDK it was compiled with is in `~/vulkan-sdk` (no system packages needed).
In Vulkan, pick the card with `GGML_VK_VISIBLE_DEVICES=N` — `HIP_VISIBLE_DEVICES` does nothing there.

### 3.3 Quantization: when fewer bits do not buy speed

| Model | Bigger quant | Smaller quant | Speed gain | Decision |
|---|---|---|---:|---|
| Qwen3.6-35B-A3B | UD-Q5_K_XL 111.3 | UD-Q4_K_XL 114.7 | +3 % | keep **Q5** |
| Gemma 4 26B-A4B | Q8_0 99.6 | UD-Q6_K_XL 103.4 | +4 % | keep **Q8_0** |
| Qwen3.8-Flash-Next | UD-Q5_K_XL 36.1 | UD-Q4_K_XL 36.1 | 0 % | keep **Q5** |

When the gain is a few percent, the higher-precision file wins: "without losing intelligence" costs almost nothing.

### 3.4 Using four cards: split one model, or run four copies

- **Layer split** (`-sm layer`): each card holds a slice of the layers and they work *one after another*.
  It lets a model bigger than one card run, but it does **not** make one agent faster.
- **Tensor split** (`-sm tensor`): every card holds a slice of *every* layer and they work together on each token.
  It made DeepSeek-V4-Flash 2× faster (23.5 → ~50 tok/s), but did nothing for Qwen3.8 (see 3.6).
- **Copies** (`qwen3.6-35b-a3b-x4`): a model that fits on one card runs as **four independent copies**, one per card.
  One agent is no faster, but four agents are four times faster in total. That is the pool:

| Agents at once | Per agent (no spec.) | Per agent (with n-gram spec.) | Total (no spec.) | Total (with n-gram) |
|---:|---:|---:|---:|---:|
| 1 | 109 | **130** | 105 | 124 |
| 4 | 110 | **203** | 418 | 481 |
| 8 | 84 | — | 590 | — |
| 12 | 71 | **107** | 677 | 596 |

At 12 agents all four cards run ~94 % busy at their 250 W power limit — the hardware is fully used.
Raising `POWER_W` in `/usr/local/sbin/gpu-tuning.sh` (max 300 W) would buy more at high load, at the cost of heat.

**How the pool routes requests** (`~/.config/llama-swap/llama-pool.py`): llama-server keeps a conversation's
history in the slot that served it, so the next turn only has to read the *new* tokens — if it lands on the same
copy. Otherwise the copy reads the whole history again (10–30 s for a long agent session). The pool therefore
recognises a conversation by its first two messages (system prompt + first user message, which never change),
sends follow-up turns back to the copy that has it cached, and sends everything else to the least busy copy.
`curl localhost:8080/upstream/qwen3.6-35b-a3b-x4/pool` (while it is loaded) shows requests in flight per GPU.

### 3.5 Speculative decoding: guess cheaply, verify in one pass

The big model can check several proposed tokens in **one** forward pass for almost the price of one token.
If a cheap "drafter" guesses the next few tokens right, you get several tokens per pass. Output is identical to
normal decoding (every token is verified), so there is **no quality loss** — only speed.

| Drafter | What guesses | Used for | Measured |
|---|---|---|---|
| `ngram-mod` | repeats of text already in the context | Qwen3.6, Gemma 4 | Qwen3.6: 107.8 → 122.2 tok/s avg; 0 % cost when nothing repeats; code/translation up to 150 |
| `draft-mtp` | the model's own multi-token-prediction head (separate small GGUF) | Qwen3.8, Gemma 4 | Qwen3.8: 33 → 70 tok/s; Gemma 4: 100 → 163 |
| `draft-dflash` | a block-diffusion drafter (DFlash2) | tested on Qwen3.8 | same as MTP (69.0) — the model's sparse attention caps it at ~4 tokens per pass |
| `draft-dspark` | DeepSeek's own draft head | DeepSeek | 23 → 33 tok/s (layer split); see SPEC-DECODING.md |

Speculation helps most where output is predictable: tool calls (JSON), code edits, translation. It helps
least in free prose at high temperature.

### 3.6 Qwen3.8-Flash-Next: why ~70 and not 100+ tok/s

Arithmetic says a 6B-active model should decode at ~100 tok/s *without* a drafter. We got 33–36, so we profiled it
(`rocprofv3 --kernel-trace --stats` on `llama-bench -n 32`):

- llama.cpp runs **~3,400 small GPU kernels per token** for this brand-new architecture (`qwen4exp`: Gated DeltaNet +
  QSA sparse attention + hyper-connections + an n-gram embedding table). Each kernel costs a few microseconds
  however little it does.
- In tensor mode each card did only ¼ of the work, yet spent **the same 21 ms per token** — proof that the kernels
  are latency-bound, not bandwidth-bound.

What we tried, and what it gave (base decode, no drafter):

| Change | tok/s |
|---|---:|
| ROCm layer split (start) | 32.6 |
| ROCm tensor split / `GGML_CUDA_ALLREDUCE=internal` / RCCL build | 31.8–34.5 |
| Vulkan layer split | 27.4 |
| HIP graphs off / `GGML_CUDA_GRAPH_OPT=1` | 30.0 / 32.6 |
| UD-Q4_K_XL instead of Q5 / 3 GPUs instead of 4 | 36.1 / 36.2 |
| CPU `performance` governor | +1 % (reverted) |
| GPU power profile **COMPUTE** | **35.5 (+9 %)** — kept, set at boot |
| newest llama.cpp (e86f5fd, fused QSA kernels) | **36.1** — kept |
| + MTP drafter, 4 tokens | **~70** |

So 100+ for *every* kind of output is not reachable with today's llama.cpp; tool calls (78–97) are close.
Two requests at once do not help either: each runs at ~38 tok/s (~69 total), because batching uses up the room
that speculation relies on. Use Qwen3.8 for one hard conversation at a time; use the pool for many agents.
llama.cpp is optimising this architecture actively (three relevant changes in the week of 20–27 Oct 2026), so:

- **Re-test monthly**: `git clone` a new llama.cpp next to the others, build it (section 5), point the
  `qwen3.8-flash-next` entry at it, run `bench_spec.py qwen3.8-flash-next`.
- **Merged-tensor GGUF** (llama.cpp PR #31028, +7 % reported): needs re-converting from the original weights
  (~360 GB download) — worth it once someone publishes such a GGUF.

### 3.7 GPU power profile

The cards now boot with the **COMPUTE** power profile (`/usr/local/sbin/gpu-tuning.sh`, block "power profile
COMPUTE"; backup of the old script: `gpu-tuning.sh.bak-20261027`). It keeps clocks up between short kernels.
Check with `rocm-smi --showprofile` (the active one has a `*`). The 250 W limit and fan curve are unchanged.

---

## 4. Where things are

| What | Where |
|---|---|
| llama-swap config | `~/.config/llama-swap/config.yaml` (backups `config.yaml.bak-20261027-*`) |
| Pool launcher | `~/.config/llama-swap/llama-pool.py` (copy in this repo: `serving/llama-pool.py`) |
| llama.cpp builds | `~/llama.cpp` (680a036, Bielik + DeepSeek-nospec), `~/llama.cpp-0ce8cd1` (ROCm, DeepSeek), `~/llama.cpp-0ce8cd1-vulkan` (Vulkan: Qwen3.6, Gemma 4), `~/llama.cpp-e86f5fd` (ROCm, newest: Qwen3.8) |
| Models | `~/models/{qwen3.8-flash-next, qwen3.6-35b-a3b, gemma-4-26b-a4b, DeepSeek-V4-Flash-0731-GGUF, bielik-11b, embed}` |
| Removed models | in the desktop trash (~490 GB): `gio trash --empty` frees the space for good |

Removed on 2026-10-27 (superseded): qwen3-235b-a22b (2 copies), gpt-oss-120b, laguna-s-2.1, qwen3-next-80b,
qwen3-32b, gpt-oss-20b (and its CPU entry `gpt-oss-20b-cpu`; `agent-server.sh` still works with any GGUF via
`AGENT_MODEL=`).

---

## 5. Recipes

**Run a different number of agents in the pool.** In the `qwen3.6-35b-a3b-x4` entry: `--slots 3` = agents per GPU,
`--gpus 0,1,2,3` = which cards. More slots per card → more agents, each a bit slower (see 3.4); keep
`--ctx-size` (shared per card) so that it still fits: ~20 KiB per token of context for Qwen3.6.

**Add a model.** Download into its own folder under `~/models/`, run `bench-model <path> --quick`, copy the
nearest existing entry in `config.yaml`, change `-m`, and (single-card MoE) try the Vulkan build first.
llama-swap reloads the config by itself (`-watch-config`).

**Measure like this guide did.**
```bash
cd ~/Desktop/github_repos/local-llm-perf-bench/server-bench
BENCH_REPS=1 python3 bench_spec.py <model> out.json          # one agent, 4 tasks x 2 temperatures
BENCH_N=1,4,8,12 python3 bench_conc.py <model> out.json      # several agents at once
```

**Build a llama.cpp (ROCm / Vulkan).**
```bash
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git ~/llama.cpp-new && cd ~/llama.cpp-new
# ROCm:
HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1201 -DCMAKE_BUILD_TYPE=Release
# or Vulkan:  source ~/vulkan-sdk/1.4.363.0/setup-env.sh && cmake -B build -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j16 --target llama-server llama-bench
```

**Profile a slow model** (what found the Qwen3.8 bottleneck):
```bash
rocprofv3 --kernel-trace --stats --output-format csv -d out -o run -- \
  llama-bench -m <model.gguf> -ngl 999 -p 0 -n 32 -r 1
# out/run_kernel_stats.csv: time and call count per kernel. Divide by ~33 tokens for "per token".
```

**Troubleshooting.**
- *502 Bad Gateway / "upstream process exited"* — usually out of VRAM at the first request (compute buffers are
  allocated then). Lower `--ctx-size`. Start the same command by hand to see `cudaMalloc failed: out of memory`.
- *A GPU stays full after unloading* — a llama-server survived; `ss -tlnp | grep llama` and `kill <pid>`.
  (Never `pkill -f` with a pattern that also matches your own command line.)
- *Pool says `loading` forever* — one copy failed; `curl -m 5 localhost:8080/logs/stream/upstream` (or the Logs
  page of the llama-swap UI) shows each copy's output prefixed `[gpuN]`.

## 6. Security reminder

llama-swap listens on `0.0.0.0:8080` without a password, and every model runs with `--agent`, whose built-in
`exec_shell_command` tool runs commands as `mkoniu`. Anyone on the LAN can use both. Keep the rig on a trusted
network (see SERWOWANIE-MODELI.md, section "Bezpieczeństwo").
