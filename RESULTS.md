# Results

Measured on the reference rig ([hardware.md](hardware.md)). The tables below are rebuilt by
`tools/build_results.py` from `quality/*/summary.json` and `perf/all-benchmark-results.md`; the findings
are written by hand. How to read them: [README](README.md#how-to-read-the-results). Several agents sharing one
model at the same time: [PARALLEL.md](PARALLEL.md).

## Findings

<!-- FINDINGS:START -->
### 2026-10-11: hard suite, DeepSeek-V4-Flash-0731 vs gpt-oss-20b (k = 3, vendor-recommended settings)

- **The hard suite separates models clearly.** Both models ran the same 20 tasks, in Polish and English, 3 attempts each:
  - DeepSeek-V4-Flash-0731 (UD-IQ3_XXS, 4 GPUs) scored **92 (PL) / 93 (EN)**.
  - gpt-oss-20b scored **47 / 52**.
  - The paired difference is **+42 points** (95% CI +28 to +55): research +62, multi-step agents +35, long
    documents +32.
- **DeepSeek is nearly flawless on agent tasks: 97 in both languages.**
  - It handled the expense claims, the business trip, the reschedule cascade, the inbox triage and the deadline chain
    perfectly in all 6 attempts.
  - Its only agent miss: in 2 of 6 meeting-planning attempts it booked Friday 10:00, although Thursday 14:00 was the
    earliest slot with a free room.
- **Where DeepSeek still fails:**
  - **The 600-row order/invoice reconciliation: 0 of 6.** Every attempt spent the whole 16k-token budget reasoning row
    by row (13 minutes each) and never gave an answer.
  - **One incident-log attempt** miscounted the database errors.
  - **The tax-relief question, 1 of 3 attempts per language.** It recognised the name of a real Polish relief
    (*ulga na start*, a social-security exemption with no cap), trusted its own knowledge over the frozen web, and
    answered "no confirmed data". **This is a flaw in the case, not the model:** the fictional name collides with a
    real one. It will be renamed in the next version of the suite.
- **gpt-oss-20b's answers look plausible and are wrong.** In this run it:
  - converted EUR 310 at 4.2650 to PLN 1,323.15 (correct: 1,322.15);
  - skipped a laptop invoice;
  - set "the Friday before the board meeting" to a Tuesday or a Wednesday;
  - booked the meeting on the wrong day;
  - picked a train that arrives too late or is cancelled;
  - cited sources that are not in the frozen web.
- **Reliability (all 3 attempts succeed) on agent and research tasks:** DeepSeek 83 / 83, gpt-oss-20b 8 / 0.
- **What the quality costs:** DeepSeek needed 6.5 h for 120 answers (median 146 s per task at 22.5 tok/s);
  gpt-oss-20b needed 1 h (21 s at 122 tok/s).
- **Neither model is credibly worse in Polish:** DeepSeek −1 (CI −2 to 0), gpt-oss-20b −6 (CI −18 to +5).
- **Caveats:**
  - The Polish cases are still `review: pending-owner` (not yet reviewed by a native speaker).
  - 20 tasks give wide per-family CIs.
  - Everything is graded by code; the hard suite has no LLM-judged checks.
<!-- FINDINGS:END -->

## Quality next to speed

<!-- TABLE:START -->
| Model | 🇵🇱 Quality | 🇬🇧 Quality | PL − EN | Agents 🇵🇱 / 🇬🇧 | Research 🇵🇱 / 🇬🇧 | Long docs 🇵🇱 / 🇬🇧 | Reliability 🇵🇱 / 🇬🇧 | Decode tok/s | Prompt tok/s | GPUs | Runs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **DeepSeek-V4-Flash-0731** <sub>UD-IQ3_XXS · `recommended` · k=3</sub> | 92 <sub>(81–99)</sub> | 93 <sub>(82–100)</sub> | −1 | 97 / 97 | 94 / 94 | 86 / 88 | 83 / 83 | 24.71 | 560 | 4×R9700 (0,1,2,3) | [quality](quality/20261010-221652-deepseek-v4-flash-0731-recommended-hard/report.md) · [speed](perf/20260930-221230/report.md) |
| **gpt-oss-20b** <sub>MXFP4 · `recommended` · k=3</sub> | 47 <sub>(34–61)</sub> | 52 <sub>(40–66)</sub> | −6 | 60 / 64 | 30 / 35 | 51 / 59 | 8 / 0 | 149.53 | 5726 | 1×R9700 (0) | [quality](quality/20261011-044658-gpt-oss-20b-recommended-hard/report.md) · [speed](perf/20260930-125802/report.md) |

Hard suite: 20 tasks, each in Polish and English: multi-step agent workflows, multi-hop research on a frozen web, and analysis of documents of 5k–14k tokens, built so that only frontier models should get close to 100 ([what is in it](https://github.com/michal-koniu/local-llm-quality-bench#the-hard-suite)). Quality: 0–100, mean of the three families, 95% CI in brackets, partial credit per task. Reliability = pass^k on agent and research tasks (the chance that **all** k attempts succeed).

Speed: decode `tg128` and prompt `pp512` from the latest valid perf run of the same model on the same machine. Per-family scores with CIs: [quality/leaderboard.md](quality/leaderboard.md); every speed measurement: [perf/all-benchmark-results.md](perf/all-benchmark-results.md).
<!-- TABLE:END -->

## Runs

<!-- RUNS:START -->
### Quality runs

| Date | Suite | Model | Preset | k | Judge | Tool commit (as recorded) | Report |
|---|---|---|---|---|---|---|---|
| 2026-10-11 | hard | gpt-oss-20b | `recommended` | 3 | none (all code-graded) | `a613e07fdf` | [20261011-044658-gpt-oss-20b-recommended-hard](quality/20261011-044658-gpt-oss-20b-recommended-hard/report.md) |
| 2026-10-10 | hard | DeepSeek-V4-Flash-0731 | `recommended` | 3 | none (all code-graded) | `a613e07fdf` | [20261010-221652-deepseek-v4-flash-0731-recommended-hard](quality/20261010-221652-deepseek-v4-flash-0731-recommended-hard/report.md) |

### Speed runs

| Date | Model | Configs | Report |
|---|---|---|---|
| 2026-10-27 | qwen3.8-flash-next-ud-q5_k_xl | throughput | [20261027-180025](perf/20261027-180025/report.md) |
| 2026-10-27 | gemma-4-26b-a4b | throughput | [20261027-175838](perf/20261027-175838/report.md) |
| 2026-10-27 | qwen3.6-35b-a3b | throughput | [20261027-154622](perf/20261027-154622/report.md) |
| 2026-09-30 | deepseek-v4-flash-0731 | thermal, throughput | [20260930-221230](perf/20260930-221230/report.md) |
| 2026-09-30 | qwen3-next-80b | throughput | [20260930-125943](perf/20260930-125943/report.md) |
| 2026-09-30 | gpt-oss-20b | throughput | [20260930-125802](perf/20260930-125802/report.md) |
| 2026-09-30 | deepseek-v4-flash | thermal, throughput | [20260930-122320](perf/20260930-122320/report.md) |
| 2026-09-30 | qwen3-235b-a22b-q3 | thermal, throughput | [20260930-121339](perf/20260930-121339/report.md) |
| 2026-09-29 | qwen3-235b-a22b | 3gpu-manual | 20260929-0945 (manual, no run folder) |
| 2026-09-29 | laguna-s-2.1 | 3gpu-manual | 20260929-0930 (manual, no run folder) |
| 2026-09-28 | gpt-oss-120b | 3gpu-manual | 20260928-2300 (manual, no run folder) |
| 2026-09-20 | gpt-oss-20b | 2gpu-manual | 20260920-1540 (manual, no run folder) |
| 2026-09-20 | qwen3-next-80b | 2gpu-manual | 20260920-1525 (manual, no run folder) |
| 2026-09-20 | qwen3-32b | 2gpu-layer | [20260920-134642](perf/20260920-134642/report.md) |
| 2026-09-19 | bielik-11b | thermal, throughput | [20260919-231520](perf/20260919-231520/report.md) |
| 2026-09-19 | qwen3-32b | thermal, throughput | [20260919-225407](perf/20260919-225407/report.md) |
| 2026-09-15 | gpt-oss-20b | throughput | [20260915-164813](perf/20260915-164813/report.md) |
<!-- RUNS:END -->
