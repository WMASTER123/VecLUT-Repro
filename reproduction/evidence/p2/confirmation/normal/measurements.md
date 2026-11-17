# P2 measurements

Single matrix operator; synthetic inputs; not end-to-end model tokens/s.

| shape | mode | N | threads | median us | CV |
|---|---|---:|---:|---:|---:|
| bitnet_square | direct | 1 | 1 | 1721.50 | 8.4% |
| bitnet_square | direct | 16 | 1 | 2133.15 | 6.6% |
| bitnet_square | direct | 31 | 1 | 2791.30 | 5.6% |
| bitnet_square | direct | 63 | 1 | 5865.21 | 2.9% |
| bitnet_square | direct | 64 | 1 | 5886.37 | 2.6% |
| bitnet_square | direct | 512 | 1 | 49870.23 | 2.6% |
| bitnet_square | graph | 1 | 1 | 1811.13 | 6.7% |
| bitnet_square | graph | 1 | 2 | 1210.46 | 4.2% |
| bitnet_square | graph | 1 | 4 | 892.12 | 2.2% |
| bitnet_square | graph | 16 | 1 | 2348.65 | 2.4% |
| bitnet_square | graph | 16 | 2 | 1507.64 | 10.9% |
| bitnet_square | graph | 16 | 4 | 1093.81 | 4.8% |
| bitnet_square | graph | 31 | 1 | 3181.74 | 4.4% |
| bitnet_square | graph | 31 | 2 | 2383.32 | 13.9% |
| bitnet_square | graph | 31 | 4 | 1527.05 | 5.5% |
| bitnet_square | graph | 63 | 1 | 6645.42 | 2.7% |
| bitnet_square | graph | 63 | 2 | 4019.69 | 10.3% |
| bitnet_square | graph | 63 | 4 | 2550.09 | 5.4% |
| bitnet_square | graph | 64 | 1 | 6701.61 | 2.3% |
| bitnet_square | graph | 64 | 2 | 4668.00 | 2.9% |
| bitnet_square | graph | 64 | 4 | 2524.22 | 6.3% |
| bitnet_square | graph | 512 | 1 | 55732.86 | 2.3% |
| bitnet_square | graph | 512 | 2 | 30365.98 | 1.3% |
| bitnet_square | graph | 512 | 4 | 16375.36 | 2.3% |
| falcon_square | direct | 1 | 1 | 646.75 | 2.1% |
| falcon_square | direct | 16 | 1 | 913.13 | 1.6% |
| falcon_square | direct | 31 | 1 | 1167.77 | 1.9% |
| falcon_square | direct | 63 | 1 | 2286.40 | 2.7% |
| falcon_square | direct | 64 | 1 | 2308.80 | 2.3% |
| falcon_square | direct | 512 | 1 | 20445.21 | 2.4% |
| falcon_square | graph | 1 | 1 | 712.26 | 6.2% |
| falcon_square | graph | 1 | 2 | 590.27 | 5.0% |
| falcon_square | graph | 1 | 4 | 491.77 | 1.0% |
| falcon_square | graph | 16 | 1 | 1039.77 | 1.8% |
| falcon_square | graph | 16 | 2 | 905.11 | 9.4% |
| falcon_square | graph | 16 | 4 | 637.65 | 5.9% |
| falcon_square | graph | 31 | 1 | 1369.01 | 1.8% |
| falcon_square | graph | 31 | 2 | 1012.47 | 16.8% |
| falcon_square | graph | 31 | 4 | 795.53 | 3.6% |
| falcon_square | graph | 63 | 1 | 2778.16 | 4.3% |
| falcon_square | graph | 63 | 2 | 2260.02 | 12.8% |
| falcon_square | graph | 63 | 4 | 1313.90 | 4.3% |
| falcon_square | graph | 64 | 1 | 2830.95 | 2.8% |
| falcon_square | graph | 64 | 2 | 2336.91 | 5.2% |
| falcon_square | graph | 64 | 4 | 1420.20 | 6.6% |
| falcon_square | graph | 512 | 1 | 24261.29 | 3.8% |
| falcon_square | graph | 512 | 2 | 14085.65 | 5.5% |
| falcon_square | graph | 512 | 4 | 7810.73 | 4.2% |
