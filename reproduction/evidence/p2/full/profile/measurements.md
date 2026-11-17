# P2 measurements

Single matrix operator; synthetic inputs; not end-to-end model tokens/s.

| shape | mode | N | threads | median us | CV |
|---|---|---:|---:|---:|---:|
| bitnet_down | direct | 128 | 1 | 44337.77 | 1.6% |
| bitnet_down | graph | 128 | 1 | 48501.92 | 3.0% |
| bitnet_down | graph | 128 | 2 | 21045.35 | 3.2% |
| bitnet_down | graph | 128 | 4 | 11251.86 | 25.4% |
| bitnet_square | direct | 1 | 1 | 1704.48 | 11.0% |
| bitnet_square | direct | 32 | 1 | 2862.81 | 2.8% |
| bitnet_square | direct | 33 | 1 | 4718.17 | 3.1% |
| bitnet_square | direct | 128 | 1 | 12109.68 | 2.9% |
| bitnet_square | graph | 1 | 1 | 1827.23 | 7.7% |
| bitnet_square | graph | 1 | 2 | 1112.95 | 8.4% |
| bitnet_square | graph | 1 | 4 | 937.98 | 8.8% |
| bitnet_square | graph | 32 | 1 | 3234.59 | 2.8% |
| bitnet_square | graph | 32 | 2 | 2409.15 | 9.4% |
| bitnet_square | graph | 32 | 4 | 1540.75 | 12.7% |
| bitnet_square | graph | 33 | 1 | 5218.61 | 3.9% |
| bitnet_square | graph | 33 | 2 | 3560.31 | 1.5% |
| bitnet_square | graph | 33 | 4 | 2741.45 | 8.5% |
| bitnet_square | graph | 128 | 1 | 13808.28 | 2.3% |
| bitnet_square | graph | 128 | 2 | 8553.25 | 5.4% |
| bitnet_square | graph | 128 | 4 | 5314.54 | 10.4% |
| falcon_square | direct | 1 | 1 | 651.90 | 4.6% |
| falcon_square | direct | 32 | 1 | 1103.38 | 1.0% |
| falcon_square | direct | 33 | 1 | 1814.06 | 2.9% |
| falcon_square | direct | 128 | 1 | 4905.86 | 4.2% |
| falcon_square | graph | 1 | 1 | 684.16 | 3.4% |
| falcon_square | graph | 1 | 2 | 575.88 | 3.1% |
| falcon_square | graph | 1 | 4 | 569.77 | 11.6% |
| falcon_square | graph | 32 | 1 | 1303.23 | 8.8% |
| falcon_square | graph | 32 | 2 | 1196.41 | 18.5% |
| falcon_square | graph | 32 | 4 | 895.57 | 9.3% |
| falcon_square | graph | 33 | 1 | 2190.05 | 5.8% |
| falcon_square | graph | 33 | 2 | 1411.31 | 9.0% |
| falcon_square | graph | 33 | 4 | 1095.70 | 6.4% |
| falcon_square | graph | 128 | 1 | 5917.47 | 2.8% |
| falcon_square | graph | 128 | 2 | 3998.52 | 9.0% |
| falcon_square | graph | 128 | 4 | 2304.00 | 11.4% |
| falcon_up | direct | 128 | 1 | 20434.23 | 2.3% |
| falcon_up | graph | 128 | 1 | 21447.29 | 2.8% |
| falcon_up | graph | 128 | 2 | 11894.37 | 4.5% |
| falcon_up | graph | 128 | 4 | 7036.74 | 4.6% |
