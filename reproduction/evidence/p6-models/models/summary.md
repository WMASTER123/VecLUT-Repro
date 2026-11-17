# P6 model OFF/ON confirmation

P=128, B=1; Decode G=16; 5 samples per variant per batch. Model loading excluded.

| Model / mode / threads | Batch 1 OFF/ON tokens/s | Speedup | Batch 2 OFF/ON tokens/s | Speedup | Max CV |
|---|---:|---:|---:|---:|---:|
| falcon3-1b-i2v4 / prefill / 1 | 73.33/74.22 | 1.012x | 73.61/73.56 | 0.999x | 5.9% |
| falcon3-1b-i2v4 / prefill / 4 | 227.77/225.44 | 0.990x | 230.46/228.47 | 0.991x | 1.8% |
| falcon3-1b-i2v4 / decode / 4 | 9.42/8.96 | 0.951x | 9.12/8.95 | 0.981x | 3.1% |
| bitnet-3b-i2v4 / prefill / 1 | 22.07/27.36 | 1.240x | 25.95/27.83 | 1.072x | 2.0% |
| bitnet-3b-i2v4 / prefill / 4 | 82.86/85.85 | 1.036x | 86.48/86.73 | 1.003x | 2.8% |
| bitnet-3b-i2v4 / decode / 4 | 3.85/4.02 | 1.044x | 4.16/4.10 | 0.987x | 3.6% |
