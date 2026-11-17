# P6 uncertainty and phase diagnostics

Bootstrap intervals are descriptive within this session, not independent multi-day evidence.
Each batch is resampled separately; ratio is the geometric mean of the two median latency ratios.

| M,K,N,T | Speedup | Descriptive 95% interval |
|---|---:|---:|
| 3200,3200,1,4 | 1.039x | [0.991, 1.087] |
| 3200,3200,32,1 | 1.091x | [1.085, 1.102] |
| 3200,3200,128,1 | 1.070x | [1.034, 1.086] |
| 3200,3200,128,4 | 1.059x | [0.984, 1.103] |
| 8640,3200,128,1 | 1.115x | [1.098, 1.128] |
| 3200,8640,128,4 | 1.015x | [0.981, 1.029] |
| 8192,2048,33,4 | 0.965x | [0.868, 1.014] |
| 17,144,33,4 | 1.022x | [0.987, 1.056] |

All phase values below are summed worker microseconds, with instrumentation enabled.
They are not formal wall-time speedups.

| Case | OFF widen | ON widen | OFF clear | ON clear |
|---|---:|---:|---:|---:|
| 0 | 68.45 | 68.32 | 34.28 | 35.18 |
| 2 | 4143.23 | 3097.67 | 275.15 | 277.94 |
| 3 | 3688.15 | 3156.31 | 128.32 | 200.93 |
| 4 | 11743.53 | 8609.14 | 804.46 | 977.71 |
