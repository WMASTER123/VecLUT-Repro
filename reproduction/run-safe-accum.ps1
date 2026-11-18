[CmdletBinding()]
param([string]$Distribution='Ubuntu-24.04',[string]$DataDirectory,[string]$StableDirectory='E:\VecLUT-Repro',[switch]$ReuseBuild)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if(-not $DataDirectory){$DataDirectory=Split-Path $repo -Parent}
New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
$data=(Resolve-Path $DataDirectory).Path
$stablePath=(Resolve-Path $StableDirectory).Path
if($data.TrimEnd('\') -eq $stablePath.TrimEnd('\')){throw 'Experiment data must be separate from stable data'}
$lr=(& wsl -d $Distribution -- wslpath -a $repo.Replace('\','/')).Trim()
$ld=(& wsl -d $Distribution -- wslpath -a $data.Replace('\','/')).Trim()
$ls=(& wsl -d $Distribution -- wslpath -a $StableDirectory.Replace('\','/')).Trim()
if(-not $ReuseBuild){
 & wsl -d $Distribution -- env "VECLUT_EXPERIMENT_DIR=$ld" "VECLUT_STABLE_DIR=$ls" bash "$lr/reproduction/run-safe-accum.sh"
 if($LASTEXITCODE -ne 0){throw 'Build/correctness failed; evidence retained'}
}
$name='experiment-'+(Get-Date -Format yyyyMMdd-HHmmss)
$result=Join-Path $data "results\$name"
$result | Set-Content -Encoding utf8 (Join-Path $data 'results\latest-experiment.txt')
& wsl -d $Distribution -- env "TMPDIR=$ld/tmp" "XDG_CACHE_HOME=$ld/cache" "PYTHONPYCACHEPREFIX=$ld/cache/pycache" python3 "$lr/reproduction/experiment_safe_accum.py" $ld "$ld/results/$name"
if($LASTEXITCODE -ne 0){throw 'Experiment failed; evidence retained'}
$decision=Get-Content -Raw (Join-Path $result 'decision.json') | ConvertFrom-Json
if($decision.status -eq 'stopped_at_kernel_gate'){
 & wsl -d $Distribution -- env "TMPDIR=$ld/tmp" "PYTHONPYCACHEPREFIX=$ld/cache/pycache" python3 "$lr/reproduction/confirm_fixed_accum.py" $ld "$ld/results/$name"
 if($LASTEXITCODE -ne 0){throw 'Fixed baseline confirmation failed; adaptive gate remains failed'}
}
& wsl -d $Distribution -- env "PYTHONPYCACHEPREFIX=$ld/cache/pycache" python3 "$lr/reproduction/analyze_safe_accum.py" "$ld/results/$name"
if($LASTEXITCODE -ne 0){throw 'Analysis failed'}
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $result 'host-cpu.json')
powercfg /getactivescheme | Set-Content -Encoding utf8 (Join-Path $result 'host-power.txt')
