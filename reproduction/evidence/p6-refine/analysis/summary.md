# P6 refinement: generated statistics

No samples excluded. Speedup = baseline median / candidate median.
Block ranges are descriptive, not confidence intervals.

## affinity

|case|model|P|threads|mode|OFF ms|candidate ms|speedup|block range|CV OFF/candidate|
|---|---|---|---|---|---|---|---|---|---|
|0|bitnet-3b-i2v4|128|1|prefill|4588.343|4251.334|1.0793|1.0500–1.1012|1.67%/2.08%|
|1|bitnet-3b-i2v4|128|1|prefill|4568.061|4206.263|1.0860|1.0759–1.1111|4.15%/2.45%|
|2|bitnet-3b-i2v4|128|1|prefill|4500.899|4165.825|1.0804|1.0592–1.0820|0.44%/1.54%|

## selective

|case|model|P|threads|mode|OFF ms|candidate ms|speedup|block range|CV OFF/candidate|
|---|---|---|---|---|---|---|---|---|---|
|0|bitnet-3b-i2v4|32|1|prefill|1119.360|1062.847|1.0532|1.0094–1.0615|1.19%/3.03%|
|1|bitnet-3b-i2v4|33|1|prefill|1676.506|1640.832|1.0217|1.0132–1.0249|1.48%/2.02%|
|2|bitnet-3b-i2v4|128|1|prefill|4901.222|4620.424|1.0608|1.0418–1.0807|1.24%/1.77%|
|3|bitnet-3b-i2v4|256|1|prefill|10492.054|9875.012|1.0625|1.0497–1.0737|0.71%/0.93%|
|4|falcon3-1b-i2v4|128|1|prefill|1856.928|1836.615|1.0111|0.9977–1.0182|1.71%/1.23%|
|5|bitnet-3b-i2v4|128|4|prefill|1526.323|1516.175|1.0067|0.9919–1.0122|2.14%/2.50%|
|6|falcon3-1b-i2v4|32|4|decode|893.756|884.965|1.0099|1.0112–1.0203|1.36%/1.16%|
|7|bitnet-3b-i2v4|32|4|decode|2026.327|1966.591|1.0304|1.0161–1.0439|2.10%/0.69%|
