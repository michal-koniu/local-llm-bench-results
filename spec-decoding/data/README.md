# Raw data: speculative decoding and tensor split

Every number in [SPEC-DECODING.md](../../SPEC-DECODING.md) comes from a file here. Files are as produced on the rig (home directory shown as `~`);
`*.json` are per-request results of `bench_spec.py`, `*.log` the console output of the same run (with the summary table at the end).

| Folder | What it contains |
|---|---|
| `01-layer-split-old-build/` | llama.cpp `680a036`, layer split: baseline (`base1`) and DSpark with different `--spec-draft-n-max` / `--spec-draft-p-min` (`spec-n<N>-p<P>`, `spec` = n 5, p-min 0) |
| `02-new-build-layer-vs-tensor/` | llama.cpp `0ce8cd1`: the 2×2 matrix of layer/tensor split with/without draft (`tmp-n-<split>-<spec/nospec>`) |
| `03-tensor-shapes-and-failures/` | slot/context shapes in tensor mode (`tmp-p2-131k`, `tmp-p2-98k`, `tmp-p4-65k`) and the failures: uneven `--tensor-split` hang (`tensor-sweep1.log`, `diag-*`), 4 slots × 131k out of memory (`tensor-p4-sweep.log`) |
| `04-agents-at-once/` | 1/2/4 agents at once (`bench_conc.py`): production before (`conc-prod`), draft with layer split (`conc-spec-par4`, `conc-final`) |
| `05-gates/` | pre-deployment gate of the tensor configuration (`candidate-gate.log`), prefill/identity test of the layer-split draft (`lossless_pp.*`), final layer-split numbers (`final.*`), VRAM sweeps (`vram3.log`) |

Notes: log lines from `llama-swap`'s upstream stream in the failure logs are interleaved from several model loads; read them with the timestamps in mind.
File names starting with `tmp-` are the temporary `llama-swap` entries the harness created and removed again.
