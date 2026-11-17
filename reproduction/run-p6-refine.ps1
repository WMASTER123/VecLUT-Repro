[CmdletBinding()]
param(
    [ValidateSet('Affinity','Screen','Selective')][string]$Stage='Selective',
    [string]$Distribution='Ubuntu-24.04',
    [string]$DataDirectory,
    [switch]$ReuseBuild
)
$ErrorActionPreference='Stop'
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if(-not $DataDirectory){$DataDirectory=Join-Path $repoPath '.repro'}
New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
$dataPath=(Resolve-Path -LiteralPath $DataDirectory).Path
$linuxRepo=(& wsl -d $Distribution -- wslpath -a $repoPath.Replace('\','/')).Trim()
$linuxData=(& wsl -d $Distribution -- wslpath -a $dataPath.Replace('\','/')).Trim()
if($LASTEXITCODE -ne 0 -or -not $linuxRepo -or -not $linuxData){throw 'Cannot resolve WSL paths'}
$run=Join-Path $dataPath ('results\p6-refine-'+$Stage.ToLower()+'-'+(Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $run | Out-Null
$linuxRun=(& wsl -d $Distribution -- wslpath -a $run.Replace('\','/')).Trim()
$run | Set-Content -Encoding utf8 (Join-Path $dataPath 'results\latest-p6-refine.txt')
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed |
    ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $run 'host-cpu.json')
powercfg /getactivescheme | Set-Content -Encoding utf8 (Join-Path $run 'host-power.txt')
if($Stage -eq 'Selective' -and -not $ReuseBuild){
    & wsl -d $Distribution -- env "VECLUT_REPRO_DIR=$linuxData" bash "$linuxRepo/reproduction/prepare-selective.sh" "$linuxRun/build"
    if($LASTEXITCODE -ne 0){throw 'Selective correctness/build failed; logs retained'}
}
$monitorScript=Join-Path $PSScriptRoot 'monitor-host.ps1'
$outputFile=Join-Path $run 'host-telemetry.jsonl'; $stopFile=Join-Path $run 'monitor.stop'
$monitorArgs=@('-NoProfile','-File',('"'+$monitorScript+'"'),'-OutputFile',('"'+$outputFile+'"'),'-StopFile',('"'+$stopFile+'"'))
$monitor=Start-Process -FilePath (Get-Command pwsh).Source -ArgumentList $monitorArgs -WindowStyle Hidden -PassThru
$monitor.Id | Set-Content (Join-Path $run 'monitor.pid')
try {
    if($Stage -eq 'Screen'){
        & wsl -d $Distribution -- env "PYTHONPYCACHEPREFIX=$linuxData/cache/pycache" python3 "$linuxRepo/reproduction/screen_widen_shapes.py" $linuxData "$linuxRun/screen" 2>&1 | Tee-Object -FilePath (Join-Path $run 'session.log')
    } else {
        $plan=if($Stage -eq 'Affinity'){'affinity.json'}else{'selective.json'}
        & wsl -d $Distribution -- env "VECLUT_REPRO_DIR=$linuxData" bash "$linuxRepo/reproduction/run-p6-refine.sh" "$linuxRepo/reproduction/plans/$plan" $linuxRun
    }
    if($LASTEXITCODE -ne 0){throw 'Refinement experiment failed; logs retained'}
} finally {
    New-Item -ItemType File -Path $stopFile -Force | Out-Null
    $monitor.WaitForExit(10000) | Out-Null
}
