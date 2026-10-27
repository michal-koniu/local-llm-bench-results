## ROCm (HIP_VISIBLE_DEVICES=1)
| model                          |       size |     params | backend    | ngl |  fa |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --: | --------------: | -------------------: |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | ROCm       | 999 |   1 |           pp512 |      3673.82 ± 94.41 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | ROCm       | 999 |   1 |          pp4096 |      3589.05 ± 16.19 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | ROCm       | 999 |   1 |           tg128 |         86.71 ± 0.95 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | ROCm       | 999 |   1 |  pp512 @ d16384 |      2998.82 ± 75.14 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | ROCm       | 999 |   1 | pp4096 @ d16384 |       2954.89 ± 4.03 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | ROCm       | 999 |   1 |  tg128 @ d16384 |         81.40 ± 0.64 |
## Vulkan (-dev Vulkan1)
| model                          |       size |     params | backend    | ngl |  fa | dev          |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --: | ------------ | --------------: | -------------------: |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | Vulkan     | 999 |   1 | Vulkan1      |           pp512 |      3459.21 ± 43.63 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | Vulkan     | 999 |   1 | Vulkan1      |          pp4096 |      3269.30 ± 15.86 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | Vulkan     | 999 |   1 | Vulkan1      |           tg128 |        111.30 ± 0.74 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | Vulkan     | 999 |   1 | Vulkan1      |  pp512 @ d16384 |      2544.95 ± 26.15 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | Vulkan     | 999 |   1 | Vulkan1      | pp4096 @ d16384 |       2520.89 ± 8.88 |
| qwen35moe 35B.A3B Q5_K - Medium |  24.76 GiB |    34.66 B | Vulkan     | 999 |   1 | Vulkan1      |  tg128 @ d16384 |        101.82 ± 0.54 |
