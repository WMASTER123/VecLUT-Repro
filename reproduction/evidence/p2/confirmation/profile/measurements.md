# P2 measurements

Single matrix operator; synthetic inputs; not end-to-end model tokens/s.

| shape | mode | N | threads | median us | CV |
|---|---|---:|---:|---:|---:|
| bitnet_down | direct | 128 | 1 | 35081.84 | 3.7% |
| bitnet_down | graph | 128 | 1 | 37667.22 | 2.4% |
| bitnet_down | graph | 128 | 2 | 20422.66 | 2.9% |
| bitnet_down | graph | 128 | 4 | 10775.60 | 1.5% |
| bitnet_square | direct | 1 | 1 | 1578.09 | 5.0% |
| bitnet_square | direct | 32 | 1 | 2816.79 | 2.9% |
| bitnet_square | direct | 33 | 1 | 4485.89 | 4.1% |
| bitnet_square | direct | 128 | 1 | 12056.61 | 2.3% |
| bitnet_square | graph | 1 | 1 | 1652.36 | 5.5% |
| bitnet_square | graph | 1 | 2 | 1095.55 | 2.5% |
| bitnet_square | graph | 1 | 4 | 862.77 | 6.3% |
| bitnet_square | graph | 32 | 1 | 3261.90 | 4.4% |
| bitnet_square | graph | 32 | 2 | 2439.72 | 5.3% |
| bitnet_square | graph | 32 | 4 | 1649.39 | 4.0% |
| bitnet_square | graph | 33 | 1 | 5003.46 | 3.3% |
| bitnet_square | graph | 33 | 2 | 3440.05 | 2.4% |
| bitnet_square | graph | 33 | 4 | 2102.28 | 3.8% |
| bitnet_square | graph | 128 | 1 | 13682.23 | 3.0% |
| bitnet_square | graph | 128 | 2 | 8605.32 | 1.9% |
| bitnet_square | graph | 128 | 4 | 5235.90 | 4.4% |
| falcon_square | direct | 1 | 1 | 653.21 | 4.3% |
| falcon_square | direct | 32 | 1 | 1119.58 | 2.3% |
| falcon_square | direct | 33 | 1 | 1751.21 | 8.4% |
| falcon_square | direct | 128 | 1 | 4892.53 | 3.2% |
| falcon_square | graph | 1 | 1 | 687.73 | 3.2% |
| falcon_square | graph | 1 | 2 | 609.23 | 5.8% |
| falcon_square | graph | 1 | 4 | 511.69 | 3.8% |
| falcon_square | graph | 32 | 1 | 1320.05 | 2.8% |
| falcon_square | graph | 32 | 2 | 1261.89 | 10.6% |
| falcon_square | graph | 32 | 4 | 838.52 | 7.3% |
| falcon_square | graph | 33 | 1 | 2013.63 | 7.5% |
| falcon_square | graph | 33 | 2 | 1649.87 | 5.8% |
| falcon_square | graph | 33 | 4 | 1177.69 | 6.5% |
| falcon_square | graph | 128 | 1 | 5907.27 | 0.7% |
| falcon_square | graph | 128 | 2 | 4215.31 | 3.5% |
| falcon_square | graph | 128 | 4 | 2776.93 | 2.9% |
| falcon_up | direct | 128 | 1 | 21853.27 | 3.4% |
| falcon_up | graph | 128 | 1 | 21952.97 | 3.9% |
| falcon_up | graph | 128 | 2 | 12166.89 | 5.1% |
| falcon_up | graph | 128 | 4 | 7049.00 | 3.7% |
