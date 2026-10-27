# Benchmark report — 20261027-154622

Config: **new-model-qwen3.6-35b-a3b** (`/tmp/bench-model-qwen3.6-35b-a3b.json`)  
Run at: 2026-10-27 15:46:22 CET

## Verdict

- ✅ **qwen3.6-35b-a3b / throughput** (250 W): pp512 **3319.5** tok/s, tg128 **79.5** tok/s

✅ Hardware error counters (PCIe AER along each GPU's path, GDDR6 ECC) unchanged on every GPU used — results are not contaminated by bus or memory errors.

## Model

| Model | Architecture | Parameters | Quant (llama.cpp type) | File | Layers | Native context |
|---|---|---|---|---|---:|---:|
| qwen3.6-35b-a3b | qwen35moe | 35B-A3B (MoE 256/8) | qwen35moe 35B.A3B Q5_K - Medium | 24.77 GiB in 1 file(s) | 40 | 262144 |

## Results

| Model | Config | Test | Mean tok/s | min | max | Spread | n |
|---|---|---|---:|---:|---:|---:|---:|
| qwen3.6-35b-a3b | throughput | pp512 | 3319.50 | 3302.51 | 3329.95 | 0.8% | 3 |
| qwen3.6-35b-a3b | throughput | tg128 | 79.46 | 74.73 | 81.85 | 9.0% | 3 |

## Per-GPU telemetry (peaks over all runs of the cell)

| Model / config | GPU | PCI | Link under load | Cap | Fan curve | Peak junction | Peak VRAM | Peak power | Peak fan |
|---|---|---|---|---:|---|---:|---:|---:|---:|
| qwen3.6-35b-a3b / throughput | gpu0 | 0000:03:00.0 | x8 Gen5 | 250 W | 55:20 65:30 75:55 82:80 90:100 | 32 °C | 32 °C | 155 W | 1815 rpm |
| qwen3.6-35b-a3b / throughput | gpu1 | 0000:06:00.0 | x4 Gen5 | 250 W | 55:15 65:30 75:55 82:80 90:100 | 44 °C | 32 °C | 147 W | 893 rpm |
| qwen3.6-35b-a3b / throughput | **all** | | | | | **44 °C** | **32 °C** | **302 W** peak sum, 95.6 W mean | |

## Effective llama-bench parameters

Read back from llama-bench's own JSON output, i.e. what actually ran — not what the config intended.

| Model / config | Split | Tensor split | FA | batch / ubatch | KV cache | Load mode | Threads | Build |
|---|---|---|---|---|---|---|---:|---|
| qwen3.6-35b-a3b / throughput | layer | 1.00/1.00 | 1 | 2048 / 512 | f16/f16 | auto | 8 | 680a036 (ROCm) |

## Hardware state at run time

| Parameter | Value |
|---|---|
| Board / BIOS | B850 AI TOP / F13c |
| CPU | AMD Ryzen 7 9700X 8-Core Processor — profile `balanced`, governor `powersave`, EPP `balance_performance` |
| RAM | 60.5 GB |
| gpu0 (HIP 0) | AMD Radeon AI PRO R9700 — gfx1201, 64 CU, 32624 MiB, 0000:03:00.0 — **used**, VBIOS `113-EXT119250-100`, subsystem `0x148c:0x2443`, idle link x8 Gen5 |
| gpu1 (HIP 1) | AMD Radeon AI PRO R9700 — gfx1201, 64 CU, 32624 MiB, 0000:06:00.0 — **used**, VBIOS `113-EXT119250-100`, subsystem `0x1eae:0x9801`, idle link x4 Gen5 |
| gpu2 (HIP 2) | AMD Radeon AI PRO R9700 — gfx1201, 64 CU, 32624 MiB, 0000:09:00.0 |
| gpu3 (HIP 3) | AMD Radeon AI PRO R9700 — gfx1201, 64 CU, 32624 MiB, 0000:19:00.0 |
| gpu4 (HIP 4) | AMD Radeon Graphics — gfx1036, 2 CU, 2048 MiB, 0000:1a:00.0 |
| GPU tuning service | active |
| llama-swap models loaded at start | [] |

## Software state at run time

| Parameter | Value |
|---|---|
| Kernel | 7.0.0-38-generic |
| Kernel cmdline | `BOOT_IMAGE=/boot/vmlinuz-7.0.0-38-generic root=UUID=2177f55b-d49b-4b63-b447-4b5d00d2e414 ro quiet splash amdgpu.ppfeaturemask=0xfff7ffff vt.handoff=7` |
| amdgpu ppfeaturemask | `0xfff7ffff` |
| ROCm | 7.2.4 |
| llama.cpp | `0ce8cd1` (2026-10-19) |
| llama.cpp build flags | `CMAKE_BUILD_TYPE=Release`, `GGML_CUDA=OFF`, `GGML_HIP=ON`, `GGML_VULKAN=OFF`, `GPU_TARGETS=gfx1201` |

## Measurement parameters

| Parameter | Value |
|---|---|
| Runs per cell | 3 — **separate OS processes** |
| Cooldown between runs | ≥ 45 s and until every GPU ≤ 50 °C (max 300 s) |
| Thermal guard | abort at junction ≥ 95 °C or VRAM ≥ 95 °C on any GPU used |
| Telemetry | amd-smi every 1.0 s, all GPUs used |

**Configurations used** — recorded verbatim:

| Config | Environment | llama-bench flags | GPUs |
|---|---|---|---|
| throughput | `HIP_VISIBLE_DEVICES=0,1`, `NCCL_PROTO=Simple`, `NCCL_P2P_DISABLE=1` | `-ngl 999 -sm layer -ts 1/1 -fa 1 -p 512 -n 128` | [0, 1] |

## How to read this

**Spread matters more than the mean.** Decode throughput on this class of card is documented as *bimodal* — the card settles into one of two modes and stays there for the life of the process. That is why every run is a separate process, not `-r N`.

- **Spread below ~2 %** → bimodality did not appear; the mean is a sensible number.
- **Spread above ~10 %, two clusters** → report both modes, not their mean.

**Peak junction near 90 °C** means you are measuring case airflow, not the model.

**Low peak power on a valid result does not mean the GPU idled** — the compute window was shorter than the sampling period. With `-sm layer` each card also works only on its share of the layers in turn, so per-card power on a multi-GPU run is naturally far below the cap; look at the summed power.

**PCIe** is the bottleneck link of each GPU's path (root port → switch on the card → GPU), read under load. The GPU endpoint itself always reports x16.

