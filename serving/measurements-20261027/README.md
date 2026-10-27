# Raw measurements behind MODEL-LINEUP.md (2026-10-27)

`spec-<entry>.json`: server-bench/bench_spec.py, one agent, 4 tasks x temperature 0/1, BENCH_REPS=1.
`conc-*.json`, `pool-conc*.json`: server-bench/bench_conc.py (BENCH_N=1,2 or 1,4,8,12).
`vk_vs_rocm_q5.md`: llama-bench, Qwen3.6-35B-A3B UD-Q5_K_XL, one card, ROCm vs Vulkan, same commit 0ce8cd1.

Entry names starting with `q38-` / `g4-` were temporary llama-swap entries; their flags are described in
MODEL-LINEUP.md section 3.5-3.6 (q38-tensor/layer = split mode; -mtpN = MTP draft with N tokens; -m- = llama.cpp e86f5fd;
-dflashN = DFlash2 drafter with N tokens; g4-mtp(-ngram) = Gemma 4 Q8_0 Vulkan with MTP (+ngram-mod)).
