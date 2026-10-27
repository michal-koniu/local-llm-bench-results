# Model lineup and serving guide — 4× Radeon AI PRO R9700

Rig: `mkoniu-B850-AI-TOP` (192.168.0.39), 4× R9700 (32 GB, gfx1201, PCIe), Ryzen 7 9700X, 60 GB RAM.
One endpoint serves everything: **llama-swap on `http://192.168.0.39:8080/v1`**. It starts a model on the
first request and stops it after 10 idle minutes — whether the model runs on llama.cpp, vLLM or radiance.

Last full measurement: 2026-10-28. Every speed below is **decode tokens/s measured from the client** with the
**vendor's recommended sampling** (`local-llm-perf-bench/server-bench/bench_stream.py`; raw data in
`serving/measurements-20261028/`). "chat" = a ~700-token answer to a short question, "code" = a rewrite after a
~14k-token source file. The first request after a start is 5–25 % slower (warm-up); ranges show both.

---

## 1. The lineup (what is in llama-swap)

Ranked by intelligence (vendor and public benchmarks; the 1st and 2nd places are clear, the rest are close).

| # | llama-swap name | Engine, cards | 1 agent tok/s | Many agents (tok/s each) | Context | Cold start | RAM |
|---|---|---|---:|---|---:|---:|---:|
| 1 | `qwen3.8-flash-next` | radiance, GPU 0+1 | **118–144** chat, **133–139** code | 4 × 89, 8 × 69 | 200k | 30 s | ~30 GB |
| 1 | `qwen3.8-flash-next-uncensored` | radiance, GPU 0+1 | 122–145 chat, 117–140 code | (same as above) | 200k | 30 s | ~30 GB |
| 2 | `qwen3.6-35b-a3b` | vLLM, GPU 2+3 | **138–147** chat, **159–172** code | 8 × 90 (~720 total) | 131k | 2–3 min | ~6 GB |
| 2 | `qwen3.6-35b-a3b-x4` | vLLM, all 4 GPUs | 141–164 chat, 197–246 code | 8 × 103 (~830), **12 × 80–85 (~1,000)** | 131k | 2–3 min | ~8 GB |
| 3 | `gemma-4-26b-a4b` | llama.cpp Vulkan, GPU 2 | 135–145 chat, 169–175 code | 2 × 93–116 | 2 × 131k | 20 s | small |
| 4 | `bielik-11b` (Polish) | llama.cpp Vulkan, GPU 0 | 48 chat, 37 code | – | 32k | 10 s | small |
| – | `qwen3.8-flash-next-llamacpp` | llama.cpp ROCm, 4 GPUs | 50–51 chat, 44–46 code | 2 × 29–38 | 131k | 1–2 min | ~50 GB* |

\* the llama.cpp version keeps Qwen3.8's 51 GB n-gram table in RAM (read lazily); it is a fallback only.

**Group `duo`:** `qwen3.8-flash-next` (GPU 0+1) and `qwen3.6-35b-a3b` (GPU 2+3) stay loaded **together** — the
smartest model for planning/review plus a fast worker, ~36 GB RAM in total. Any other model unloads everything.
Only one radiance model at a time (two would need ~60 GB RAM).

### Quick choice

| You need | Use |
|---|---|
| The best answer to a hard question; long agent tasks; code review | `qwen3.8-flash-next` |
| Same, but without refusals (security research, pentest learning) | `qwen3.8-flash-next-uncensored` |
| A fast agent / coding worker (1–8 agents) | `qwen3.6-35b-a3b` |
| 8–16 agents at once | `qwen3.6-35b-a3b-x4` |
| A smart planner and fast workers at the same time | `qwen3.8-flash-next` + `qwen3.6-35b-a3b` (group `duo`) |
| Something that starts in seconds on one card | `gemma-4-26b-a4b` |
| Polish text | `bielik-11b` |

Removed on 2026-10-28: DeepSeek-V4-Flash-0731 (41–52 tok/s at best — too slow, and Qwen3.8-Flash-Next is smarter).

---

## 2. Other configurations we measured (for specific scenarios)

Not everything belongs in llama-swap, but every setup below was run and measured on this rig. Use it when an
application needs a different split of the four cards. "How" says what to change; files are in section 6.

### 2.1 One model on ONE card

| Model, engine | 1 agent tok/s | Notes / how |
|---|---:|---|
| Gemma 4 26B-A4B Q8_0, llama.cpp **Vulkan** + MTP + n-gram | 135–145 chat, 169–175 code | in llama-swap (`gemma-4-26b-a4b`); pick the card with `GGML_VK_VISIBLE_DEVICES` |
| Qwen3.6-35B-A3B UD-Q5_K_XL, llama.cpp Vulkan + n-gram | 100–111 | the pre-vLLM entry; file still in `~/models/qwen3.6-35b-a3b/`; ROCm was 87, Q4 only +3 % |
| Qwen3.8-27B MXFP4, vLLM Radiance TP1 | 78 chat, 93–96 code | `serve-tp1.sh`; only **64k** context fits (131k fails: 3.9 GB left for KV) |
| Bielik 11B Q8_0, llama.cpp Vulkan | 48 | Vulkan +5 % over ROCm; speculative decoding gives nothing |
| Qwen3.6 FP8 on vLLM | — | does not fit one card (35 GB weights) |

### 2.2 One model on TWO cards

| Model, engine | 1 agent tok/s | Many agents | Notes |
|---|---:|---|---|
| **Qwen3.8-Flash-Next, radiance** (lossless: `--tp-wire exact`, KV bf16) | 118–144 chat, 133–139 code | 4 × 89, 8 × 69 | in llama-swap |
| Qwen3.8-Flash-Next, radiance, author's settings (`--tp-wire wht6`, KV fp8) | 78–103 chat, 108–134 code | 4 × 85–89 | lossy *and* not faster here → not used |
| **Qwen3.6-35B-A3B FP8, vLLM Radiance** (KV bf16) | 138–147 chat, 159–172 code | 8 × 90 | in llama-swap; KV fp8 was the same speed but uncalibrated |
| Qwen3.8-27B MXFP4 + DFlash2, vLLM Radiance TP2 (KV bf16) | 123–131 chat, 151–167 code | 8 × 70 | as fast as Flash-Next on the same cards but less capable → not in llama-swap |

### 2.3 Three cards

Nothing here needs exactly three cards. Useful combinations instead:
- `qwen3.8-flash-next` (GPU 0+1) + `gemma-4-26b-a4b` (GPU 2): add both to a group like `duo` (section 5).
- radiance supports `--tp 3` (`~/radiance-engine/docs/TP3.md`, attention runs on 2 of the 3 ranks) — untested;
  llama.cpp Qwen3.8 on 3 vs 4 cards made no difference.

### 2.4 One model on ALL FOUR cards

| Model, engine | 1 agent | Many agents | Notes |
|---|---:|---|---|
| **Qwen3.6-35B-A3B FP8, vLLM TP4** | 141–164 chat, 197–246 code | 8 × 103, 12 × 80–85 | in llama-swap (`-x4`); needs `concurrencyLimit` > 10 (section 4.7) |
| Qwen3.6 vLLM, 2 copies × 2 cards (`--data-parallel-size 2`) | – | – | crashed under load in one test; not pursued |
| Qwen3.6 llama.cpp, 4 copies × 1 card (`llama-pool.py`) | 109 (130 with n-gram) | 12 × 71 (677 total) | replaced by vLLM TP4; script kept in `serving/llama-pool.py` |
| Qwen3.8-Flash-Next, radiance TP4 | – | – | **pins 4 × host pool → 53 GB RAM, system swapped**; don't |
| Qwen3.8-Flash-Next, llama.cpp ROCm (layer or tensor split) | 45–51 | 2 × 29–38 | kernel-launch bound, see 4.6; fallback entry |
| DeepSeek-V4-Flash-0731, llama.cpp tensor split + DSpark | 41–43 chat, 39–52 code | 2 × ~23 | removed |

---

## 3. Using the models

| Setting | Value |
|---|---|
| Base URL | `http://192.168.0.39:8080/v1` (on the rig: `http://localhost:8080/v1`) |
| API key | anything non-empty |
| Model | a llama-swap name from section 1 (aliases: `smartest`, `uncensored`, `qwen3.6`, `qwen3.6-pool`, `gemma4`, …) |

**Context to declare in the client.** All engines share one KV pool between parallel requests. Declare a
window that still fits when several agents are long at once:

| Model | Max per request | Safe per-agent window with many agents |
|---|---:|---:|
| `qwen3.8-flash-next(-uncensored)` | 200,000 | 65,536 (4+ agents) |
| `qwen3.6-35b-a3b` / `-x4` | 131,072 | 65,536 (8+ agents) |
| `gemma-4-26b-a4b` | 131,072 | 65,536 |

### User interfaces
- **llama-swap UI** — `http://192.168.0.39:8080/ui`: model list with the descriptions from section 1, load/unload,
  logs, a Playground chat that works with every model. Clicking a model opens `http://192.168.0.39:8080/upstream/<name>/`:
  for llama.cpp models that is the model's own chat UI, for radiance models the engine's dashboard (speed, sessions),
  and for vLLM models (no page of their own; before 2026-10-27 this gave *"Not Found"*) it jumps to that model's chat
  in Open WebUI — see "vLLM front" in section 5.
  *"Agentic turn limit reached"* comes from that llama.cpp chat UI (Settings → Tools → **Agentic turns**, per
  browser, default 100). The server default is now 10,000 (`~/.config/llama-swap/ui-defaults.json`), but a browser
  that already saved settings keeps its value — change it there once.
- **Open WebUI** — `http://192.168.0.39:3000`: full chat app (history, files, system prompts) for **all** models,
  connected to llama-swap. The first account you create becomes the admin. Container `open-webui`
  (`docker restart open-webui`; data in the Docker volume `open-webui`).

### Tools and self-knowledge (both chat UIs)
Every model in both chat UIs has the same abilities and is told about them at the start of every chat:

| | Open WebUI (all 7 models) | llama.cpp chat UI (Gemma, Bielik, Flash-Next fallback) |
|---|---|---|
| Shell as `mkoniu` (Docker allowed, no sudo) | `run_command` | `exec_shell_command` (built in, `--agent`) |
| Files | `read_file`, `list_directory`, `write_file`, `edit_file` (auto-backup to `~/.cache/rig-tools/backups/`) | `read_file`, `file_glob_search`, `grep_search`, `write_file`, `edit_file`, `get_info` |
| Internet | `web_search`, `fetch_url` | `rig-web_web_search`, `rig-web_fetch_url` |
| Where they come from | tool server **rig-tools** (MCP, `http://172.17.0.1:8765/mcp`, bearer token) | llama-server `--tools all` + `--mcp-servers-config tools/mcp-web.json` (rig-tools `--stdio --web-only`) |

**System prompt per model**, generated from `config.yaml` by `~/.config/llama-swap/tools/sync_prompts.py`:
who the model is (name, id, description), engine, GPUs and its exact start command, its config files, the machine
and services, its tools (including internet), rules for changing its own configuration (back up, validate YAML,
measure with bench_stream.py, saving config.yaml restarts the model, anything needing sudo is handed to the user as
numbered steps), and `~/.config/llama-swap/AGENT_BOOTSTRAP.md` verbatim (Tor proxy, `~/ai_skills`, policy).
The prompts are readable in `~/.config/llama-swap/prompts/<id>.<ui>.md`.

**After changing config.yaml** (or AGENT_BOOTSTRAP.md), run — the models know to do this themselves:
```bash
python3 ~/.config/llama-swap/tools/sync_prompts.py     # needs the docker group for the Open WebUI part
```
It writes `~/.config/llama-swap/ui/<id>.json` (llama.cpp UI defaults: system prompt, agentic turns) and, through
Open WebUI's admin API, the rig-tools connection, "tools on by default" and each model's system prompt.
In the llama.cpp UI the prompt is a default: if you once typed your own system message in Settings, yours wins.

**Not covered:** API clients (OpenClaw, opencode, scripts) send their own system prompt and tools, so they get neither.

**Tested (27 Oct), Open WebUI, question "which model are you, where is your config; run `hostname && uptime -p`;
find the newest Open WebUI release":** all three engines answered identity and config paths correctly and used the
shell and web tools -- Gemma (llama.cpp) in 9 s, Qwen3.6 (vLLM) and Qwen3.8-Flash-Next (radiance) in ~135 s
including cold start. Qwen3.6 and Flash-Next also checked the GitHub releases page/API themselves when the search
snippet was outdated; Flash-Next verified its own entry against `localhost:8080/running` and config.yaml.
llama.cpp UI (Gemma, Bielik): system prompt served as UI default, all 9 tools listed from the LAN origin.

**rig-tools service:** `systemctl status rig-tools`; code `~/.config/llama-swap/tools/rig_tools.py`; Python venv
`~/.local/share/rig-tools/venv` (`tools/requirements.txt`, `mcp<2`); token `~/.config/rig-tools/token` (chmod 600,
also stored in Open WebUI). It listens only on the Docker bridge (172.17.0.1), not on the LAN.

### OpenClaw
`~/.openclaw/openclaw.json` (field names as of autumn 2026 — `openclaw doctor` shows differences):
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
          { "id": "qwen3.8-flash-next", "name": "Qwen3.8 Flash-Next (smartest)", "reasoning": true, "contextWindow": 131072, "maxTokens": 32768 },
          { "id": "qwen3.6-35b-a3b",    "name": "Qwen3.6 35B (fast worker)",     "reasoning": true, "contextWindow": 65536,  "maxTokens": 16384 },
          { "id": "qwen3.6-35b-a3b-x4", "name": "Qwen3.6 35B x4 (many agents)",  "reasoning": true, "contextWindow": 65536,  "maxTokens": 16384 },
          { "id": "gemma-4-26b-a4b",    "name": "Gemma 4 26B (1 GPU)",           "reasoning": true, "contextWindow": 65536,  "maxTokens": 16384 }
        ]
      }
    }
  },
  "agents": { "defaults": { "model": { "primary": "rig/qwen3.8-flash-next", "fallbacks": ["rig/qwen3.6-35b-a3b"] } } }
}
```
Main agent on `qwen3.8-flash-next`, sub-agents on `qwen3.6-35b-a3b`: both stay loaded (group `duo`).
For a swarm of 8–16 sub-agents use `qwen3.6-35b-a3b-x4` instead (it unloads the others while it runs).

### opencode, Python, curl
```json
{ "$schema": "https://opencode.ai/config.json",
  "provider": { "rig": { "name": "Local rig", "npm": "@ai-sdk/openai-compatible",
    "options": { "baseURL": "http://192.168.0.39:8080/v1" },
    "models": { "qwen3.8-flash-next": { "name": "Qwen3.8 Flash-Next" }, "qwen3.6-35b-a3b": { "name": "Qwen3.6 35B" } } } } }
```
```python
from openai import OpenAI
c = OpenAI(base_url="http://192.168.0.39:8080/v1", api_key="local")
print(c.chat.completions.create(model="qwen3.6-35b-a3b", messages=[{"role": "user", "content": "Hi"}]).choices[0].message.content)
```
```bash
curl -s http://192.168.0.39:8080/v1/models                  # configured models
curl -s http://192.168.0.39:8080/running                    # loaded now
curl -s -X POST http://192.168.0.39:8080/api/models/unload  # free all GPUs
```
**Sampling.** Each model has its vendor's sampling as the server default (Qwen3.8: temp 1.0 / top-p 0.95 / top-k 20;
Qwen3.6: 0.6 / 0.95 / 20 "precise coding"; Gemma 4: 1.0 / 0.95 / 64). A client that sends its own `temperature`
overrides it.

---

## 4. Lessons from the measurements

### 4.1 Measure with real sampling, not temperature 0
Speculative decoding (a cheap drafter guesses tokens, the model verifies several in one pass) accepts far more
guesses at temperature 0. The first lineup (2026-10-27) averaged temp-0 and temp-1.0 runs and reported Qwen3.8
at "~70" and Gemma at "~170" tok/s; with vendor sampling the same configs gave ~47 and ~140 — what the UI showed.
`bench_stream.py` therefore always takes the sampling as arguments.

### 4.2 The engine matters more than any flag
| Model | llama.cpp (best) | Best other engine | Why |
|---|---:|---:|---|
| Qwen3.8-Flash-Next | 45–51 (4 GPUs) | **118–144 (radiance, 2 GPUs)** | radiance fuses this architecture's ~3,400 small kernels per token; llama.cpp launches them one by one (4.6) |
| Qwen3.6-35B-A3B | 100–111 (1 GPU) | **138–172 (vLLM FP8, 2 GPUs)** | vLLM's MTP drafter + RDNA4-tuned MoE kernels; FP8 weights are also *more* precise than Q5 |
| Gemma 4 26B-A4B | 135–175 (1 GPU) | – | the Radiance vLLM fork has no Gemma 4 26B support yet |

### 4.3 Engines on this rig
- **llama.cpp / llama-server** (`~/llama.cpp-*`): GGUF files, any number of cards, Vulkan or ROCm builds.
  On RDNA4 **Vulkan is faster for single-card MoE** (+18–28 % Qwen3.6/Gemma, +5 % dense Bielik); ROCm for multi-card.
- **vLLM "Radiance" fork** (`stilldeadcode/vllm-radiance:0.9.3`, repo `~/radiance-vllm-mxfp4`): stock vLLM does
  not run well on gfx1201 (no AITER, broken FP8); this community fork patches it. Safetensors checkpoints
  (FP8, MXFP4), tensor parallel over 2 or 4 cards, MTP/DFlash drafters, real continuous batching.
  Cold start 2–3 min (kernel cache in `~/radiance-vllm-mxfp4/vllm-cache`).
- **radiance** (`stilldeadcode/radiance:1.13.0`, docs `~/radiance-engine/docs/`): a separate C++/HIP server for
  RDNA4 by the same author. Loads its own `.rad` containers (weights + tokenizer + template + drafter).
  Only engine that runs Qwen3.8-Flash-Next fast. Speaks OpenAI, Anthropic Messages and llama-server APIs.
  Status: young project ("early dev") — keep the llama.cpp fallback entry.

### 4.4 Lossless choices that cost nothing
| Choice | Result |
|---|---|
| KV cache **bf16** instead of uncalibrated fp8 (vLLM Qwen3.6 / Qwen3.8-27B) | same speed (139–146 vs 130–140) |
| radiance `--tp-wire exact` + KV bf16 instead of `wht6` + fp8 | faster here (118–144 vs 78–103 chat) |
| Qwen3.6 FP8 (vLLM) instead of Q5_K_XL GGUF | faster *and* closer to the original |
| Gemma Q8_0 instead of Q6_K_XL; Qwen3.6 Q5 instead of Q4 | +3–4 % speed was not worth the precision |

Quality of the 4-bit Flash-Next `.rad` file (author's measurement, ~75k positions of chat/tool/code): mean KL vs bf16
0.024 on text, top-1 agreement 94.6 % — closer to bf16 than a second bf16 implementation is (0.040 / 95.1 %).

### 4.5 Draft length per model (speculative decoding, vendor sampling)
| Model | Best | Tested | Gain |
|---|---|---|---|
| Qwen3.8 llama.cpp (MTP) | **2** | 2 / 3 / 4 / 3+p-min / 8+p-min / +ngram | 47 vs 42 at 4 (+12 %) |
| Gemma 4 (MTP + n-gram) | **4** | 2–6, ngram 16/64 | equal on chat, best on code |
| Qwen3.6 llama.cpp | n-gram only | embedded MTP GGUF (unsloth) | MTP in llama.cpp **34–40 vs 107** — broken path, don't |
| DeepSeek DSpark | 3 | 2 / 3 / 5 | 3 ≈ 5 > 2 |
| vLLM Qwen3.6 | Radiance dynamic draft (8→4 by load) | – | built into the image |
| radiance Flash-Next | MTP depth 3 | – | author default |

### 4.6 Why Qwen3.8-Flash-Next is slow on llama.cpp
rocprofv3: ~3,400 GPU kernels per token, ~23 ms per token, most of them tiny. Every kernel costs a few µs to launch
no matter how small, so speed stayed at 33–36 tok/s with layer or tensor split, Vulkan, Q4 instead of Q5, 3 or 4
cards, RCCL, HIP graphs — the limit was the implementation, not the hardware. radiance fuses those kernels
(e.g. the all-reduce with the gated-residual write) and runs the same model 3× faster on half the cards.

### 4.7 Limits found the hard way
- **RAM.** radiance pins `--host-pool-mib` *per card* plus the n-gram table. TP4 with the author's 12 GB pool
  took 53 GB of 60 → swap, memory alerts. Now: TP2, 8 GB pool, n-gram table read from disk → ~30 GB, same speed.
- **llama-swap `concurrencyLimit` defaults to 10** per model: request 11+ gets HTTP 429. The `-x4` entry has 20.
- **One card drives the monitor** (GPU 0, ~0.8 GB used): vLLM on GPU 0 needs `--gpu-memory-utilization` ≤ 0.94.
- **The power profile** COMPUTE (`/usr/local/sbin/gpu-tuning.sh`, set at boot) gave +9 % on Qwen3.8 llama.cpp.

---

## 5. How llama-swap runs Docker models (and how to add one)

llama-swap only knows "run this command, wait for `/health`, proxy to `${PORT}`, kill it later". Two small
wrappers make a container behave like such a command:

- `~/.config/llama-swap/vllm/run-compose.sh FILE.compose.yml VAR=value …` — `docker compose up -d`, follows the
  container log (visible in llama-swap's Logs), and `docker compose down` when llama-swap stops the model.
  Used by `qwen3.6-*` (vLLM) and `qwen3.8-flash-next*` (radiance).
- `~/.config/llama-swap/vllm/run-docker.sh NAME launcher …` — for launchers that start one named container
  themselves (Radiance's `serve-tp2.sh`); stops that container on exit. Used by the 27B recipe below.

**vLLM front** — vLLM has no web page, so llama-swap's model link (`/upstream/<name>/`) answered *"Not Found"*.
An entry with `CHAT_MODEL=<llama-swap id>` in its `cmd` makes `run-compose.sh` also start
`vllm/front.compose.yml`: a small nginx container (`<NAME>-front`) on `PORT` that passes every API call to vLLM
(now on `BPORT` = `PORT`+10000) unbuffered, and answers only `/` with a page that opens
`http://<host>:3000/?model=<id>` (Open WebUI). Measured through the front: same speed (chat 139–146 tok/s),
streaming and tool calls OK. Remove `CHAT_MODEL=` from an entry to go back to vLLM directly on `PORT`.

The compose files take everything that differs between entries as variables (`GPUS`, `TP`, `SEQS`, `KVDT`,
`HOSTPOOL`, `NGRAM`, `RADFILE`, …), so a new variant is a new llama-swap entry with other values, e.g. Flash-Next on
cards 2+3: `GPUS=2,3`. Containers listen on 127.0.0.1 only; the LAN goes through llama-swap.

**Run a container by hand** (debugging):
```bash
cd ~/.config/llama-swap/radiance
PORT=8000 NAME=fn-test GPUS=0,1 TP=2 WIRE=exact KVDT=bf16 docker compose -f flashnext.compose.yml up -d
docker logs -f fn-test        # Ctrl-C leaves it running
NAME=fn-test docker compose -f flashnext.compose.yml down
```

**Recipe: Qwen3.8-27B on vLLM (2 cards)** — measured in 2.2, files already on disk
(`~/models/Qwen3.8-27B-MXFP4-mtpfp8`, `~/models/Qwen3.8-27B-DFlash2-FP8`):
```yaml
  "qwen3.8-27b":
    name: "Qwen3.8-27B MXFP4 - vLLM, 2 GPU"
    cmd: |
      /home/mkoniu/.config/llama-swap/vllm/run-docker.sh vllm-qwen38-27b
      env NAME=vllm-qwen38-27b SERVED_NAMES=qwen3.8-27b PORT=${PORT} GPU_IDS=0,1 GPU_UTIL=0.94 MAXLEN=131072
      /home/mkoniu/radiance-vllm-mxfp4/serve-tp2.sh --kv-cache-dtype auto --host 127.0.0.1
      --override-generation-config '{"temperature":1.0,"top_p":0.95,"top_k":20}'
    proxy: http://127.0.0.1:${PORT}
    checkEndpoint: /health
    useModelName: qwen3.8-27b
```

**Make two models share the cards** (like `duo`): put them in one group with `swap: false`; their GPUs must not
overlap and their RAM must fit together.

**Add a radiance model**: download the `.rad` (links in `~/radiance-engine/README.md`, compose examples in
`~/radiance-engine/deploy/compose/`), copy the Flash-Next entry, set `MODELDIR`/`RADFILE`, start with TP2.

---

## 6. Where things are

| What | Where |
|---|---|
| llama-swap config | `~/.config/llama-swap/config.yaml` (backups `config.yaml.bak-2026*`; copy: `serving/llama-swap.yaml`) |
| Docker model files | `~/.config/llama-swap/vllm/` (wrappers, `qwen3.6-fp8.compose.yml`), `~/.config/llama-swap/radiance/flashnext.compose.yml` (copies: `serving/docker/`) |
| vLLM Radiance fork | `~/radiance-vllm-mxfp4` (launchers, notes `README.md`, `DOCKERHUB.md`) |
| radiance engine | `~/radiance-engine` (docs `docs/GUIDE.md`, `docs/ARCHITECTURES.md`) |
| Models | `~/models/qwen3.8-flash-next/{radiance, UD-Q5_K_XL, mtp…}`, `~/models/qwen3.8-flash-next-uncensored/radiance`, `~/models/Qwen3.6-35B-A3B-FP8`, `~/models/qwen3.6-35b-a3b/` (GGUF), `~/models/gemma-4-26b-a4b`, `~/models/bielik-11b`, `~/models/Qwen3.8-27B-*` |
| llama.cpp builds | `~/llama.cpp-0ce8cd1-vulkan` (Gemma, Bielik), `~/llama.cpp-e86f5fd` (ROCm, Flash-Next fallback), `~/llama.cpp`, `~/llama.cpp-0ce8cd1` |
| Benchmarks | `local-llm-perf-bench/server-bench/bench_stream.py` (any engine), `bench_spec.py`, `bench_conc.py` (llama.cpp only) |
| `hf` CLI | `/usr/local/bin/hf` (system-wide) |

**Measure a model like this guide:**
```bash
cd ~/Desktop/github_repos/local-llm-perf-bench/server-bench
BENCH_N=1,4,8 python3 bench_stream.py qwen3.8-flash-next 1.0 0.95 20 out.json   # model, temp, top-p, top-k
```

**Troubleshooting**
- *A Docker model never becomes ready* — `docker ps -a`, `docker logs <name>` (names: `radiance-flashnext`,
  `qwen36-vllm`, `qwen36-vllm-x4`). vLLM's first start compiles kernels (up to ~10 min); later starts 2–3 min.
- *Memory alert* — `free -g`; `docker stats --no-stream`. Only one radiance model at a time; never radiance TP4.
- *HTTP 429* — more parallel requests than the entry's `concurrencyLimit` (default 10).
- *502 from a llama.cpp model* — usually out of VRAM at the first request; lower `--ctx-size`.

## 7. Security
llama-swap (`:8080`) and Open WebUI (`:3000`) listen on the LAN. The models can run shell commands as `mkoniu`
(who is in the docker group, which is root-equivalent) and reach the internet. In Open WebUI only admin accounts get
the rig-tools tools (connection without access grants); llama-swap has no password, so anyone on the LAN can use the
llama.cpp chat UI and its tools. The models get no sudo password on purpose. The uncensored model answers
anything. Keep the rig on a trusted network. Docker containers listen on 127.0.0.1 only.
