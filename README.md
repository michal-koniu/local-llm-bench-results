# local-llm-bench-results

**Which open model should run your local agent or assistant, in Polish and English, and how fast?**
Quality and speed of open-weight LLMs, measured on one home rig with 4× AMD Radeon AI PRO R9700 (128 GB VRAM).

![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey)
![Quality: local-llm-quality-bench](https://img.shields.io/badge/quality-local--llm--quality--bench-blue)
![Speed: local-llm-perf-bench](https://img.shields.io/badge/speed-local--llm--perf--bench-blue)

➡️ **[MODEL-LINEUP.md](MODEL-LINEUP.md)**: the models served on the rig now, ranked by intelligence and measured speed, with ready-made OpenClaw / opencode settings.

➡️ **[RESULTS.md](RESULTS.md)**: the leaderboard (quality next to speed), findings, and every run with its date.

Every number here comes from two open-source tools, and every run folder contains everything needed
to reproduce it:

- **[local-llm-quality-bench](https://github.com/michal-koniu/local-llm-quality-bench)**: every quality
  result here uses its **hard suite**, the same 20 tasks in Polish and English for every model: multi-step agent
  workflows in a mock workspace, multi-hop research on a frozen web, and analysis of documents of 5k–14k tokens.
  Built so that only frontier models should get close to 100, and graded entirely by code.
- **[local-llm-perf-bench](https://github.com/michal-koniu/local-llm-perf-bench)**: llama.cpp throughput
  with the conditions recorded (power cap, PCIe links, temperatures, error counters, effective parameters).

## Project map

Four repos, one job each:

| Repo | What it is | It changes when… |
|---|---|---|
| [local-llm-perf-bench](https://github.com/michal-koniu/local-llm-perf-bench) | **Tool**: how fast a model runs (llama.cpp, any GGUF, 1–n GPUs) | the way speed is measured changes |
| [local-llm-quality-bench](https://github.com/michal-koniu/local-llm-quality-bench) | **Tool**: how good a model is as an agent/assistant, in Polish and English | cases, scorers or model profiles change |
| [local-llm-bench-results](https://github.com/michal-koniu/local-llm-bench-results) | **Data**: everything measured on the reference rig, quality next to speed | a benchmark run finishes |
| [radeon-r9700-rocm-notes](https://github.com/michal-koniu/radeon-r9700-rocm-notes) | **Platform**: making 4× Radeon AI PRO R9700 + ROCm work (setup, traps, monitoring, tuning) | hardware, drivers or the serving stack change, or a new trap is found |

## What's here

```
RESULTS.md                  leaderboard, findings and the list of runs (rebuilt by tools/build_results.py)
quality/                    local-llm-quality-bench output ($QBENCH_RESULTS)
  leaderboard.md              every quality run side by side, per family and language, with CIs
  <run-id>/report.md          one run: scores, worst failures, how to replicate
  <run-id>/samples.jsonl      every answer, with the exact request that produced it
  <run-id>/grades.jsonl       every check's score and reason (judge verdicts included)
  <run-id>/manifest.json      model file, server build, chat-template hash, samplers the server used
perf/                       local-llm-perf-bench output ($LLM_PERF_RESULTS)
  all-benchmark-results.md    every speed measurement with its conditions
  <run-id>/report.md          one run: verdict, per-GPU telemetry, hardware/software state
  configs/                    the rig's tuned multi-GPU configs (tensor splits for 2, 3 and 4 cards)
serving/llama-swap.yaml     how the models are served (flags, context, ubatch, chat templates)
PARALLEL.md                 several agents sharing one model at once: speed per agent and in total
SPEC-DECODING.md            speculative decoding and tensor split: how much faster one agent gets, and what it costs
spec-decoding/data/         the raw per-request results and logs behind SPEC-DECODING.md
orchestrator/               a small model on the CPU that runs the benchmarks of the big ones
hardware.md                 the machine
COMMIT-MAP.md               tool commits as recorded in runs -> the same commits on GitHub
tools/build_results.py      rebuilds RESULTS.md from quality/ and perf/
```

## How to read the results

- **Polish and English are never pooled.** A model that is great in English and weak in Polish shows exactly that.
- **CIs matter.** A few dozen tasks × a few samples separate a good configuration from a bad one, not two good
  ones a few points apart. Overlapping intervals mean "not distinguishable at this size".
- **Reliability ≠ average.** For an assistant you rely on, pass^k (all k attempts succeed) matters more than the mean.
- **Read the transcripts.** Every report lists its worst failures; `samples.jsonl` has the full conversation for each.
- **Settings are the vendor's** unless a run's preset says otherwise: each model profile cites where its sampling
  settings come from. Models are served by llama.cpp through llama-swap, quantised as shown.
- **Caveats that apply to a run** (review status of cases, judge calibration) are stated in its `report.md`.

## Reproduce a result

1. Check out the tool at the version named in the run's `manifest.json` (`bench.commit`; see
   [COMMIT-MAP.md](COMMIT-MAP.md) if the hash is not found on GitHub; releases are tagged).
2. Get the same GGUF (`manifest.json → model.profile.weights`) and serve it with the same flags
   (`manifest.json → server.llama_swap.cmd`, or [serving/llama-swap.yaml](serving/llama-swap.yaml)).
3. Run the same model profile and preset, then compare:
   `python3 -m qbench compare runs/<yours> path/to/quality/<run-id>`.

Or replay a single answer: every line of `samples.jsonl` holds the exact request body. See the quality bench's
[docs/REPLICATE.md](https://github.com/michal-koniu/local-llm-quality-bench/blob/main/docs/REPLICATE.md).

## Add a run

```bash
# quality (writes to $QBENCH_RESULTS = this repo's quality/)
python3 -m qbench run --model <profile> --suite hard --k 3 && python3 -m qbench grade runs/<run-id> \
  && python3 -m qbench report runs/<run-id> --publish
# speed (writes to $LLM_PERF_RESULTS = this repo's perf/)
bench-model <model>
# then
python3 tools/build_results.py && git add -A && git commit -m "<model>: quality and speed"
```

Or let the [orchestrator](orchestrator/README.md) do it: `python3 orchestrator/agent.py "Measure <model> fully."`

## Run the benches on your own models

Both tools are MIT-licensed and model- and machine-independent. Point `QBENCH_RESULTS` and `LLM_PERF_RESULTS`
at a repo like this one, and you have your own leaderboard. If your numbers on the same weights differ from
mine, please open an issue in the relevant tool repo: that's a finding about the serving stack.

## License

The data (results, transcripts, reports) is **CC BY 4.0**: reuse it, with attribution. The scripts in `tools/`
and `orchestrator/` are **MIT**. See [LICENSE.md](LICENSE.md).
