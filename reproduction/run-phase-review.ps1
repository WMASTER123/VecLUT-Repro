param([ValidateSet('Evidence','Recheck','Diagnose')][string]$Stage='Evidence')
$ErrorActionPreference='Stop'
if ($Stage -eq 'Evidence') {
    $base=Join-Path $PSScriptRoot 'evidence/p65'
    $repeat=Get-Content (Join-Path $base 'recheck/decision.json') -Raw | ConvertFrom-Json
    $gate=Get-Content (Join-Path $base 'lanes/screen/gate.json') -Raw | ConvertFrom-Json
    Write-Output 'Archived measurements; this command does not rerun benchmarks.'
    Write-Output ('Continuous INT32 repeat: passed={0}; main good={1}/8; unresolved noise={2}' -f $repeat.passed,$repeat.main_good,$repeat.unresolved_noise.Count)
    Write-Output ('Valid lanes: good={0}/{1}; consistent regressions={2}; failed guards={3}; model gate={4}' -f $gate.target_both_batches_ge_10pct,$gate.target_configs,$gate.target_consistent_regressions.Count,$gate.failed_guards.Count,$gate.proceed_to_models)
    Write-Output (Join-Path $PSScriptRoot 'VALID_LANES_REPORT.md')
    return
}
# Local exact-binary repeat: requires the documented E-drive experiment layout.
$repo=(& wsl -d Ubuntu-24.04 -- wslpath -a -u (Split-Path $PSScriptRoot)).Trim()
if($LASTEXITCODE -ne 0){throw 'Cannot resolve the repository in WSL'}
$root=(& wsl -d Ubuntu-24.04 -- dirname $repo).Trim()
if($LASTEXITCODE -ne 0){throw 'Cannot resolve experiment root'}
if($Stage -eq 'Recheck') {
    & wsl -d Ubuntu-24.04 -- env "PYTHONPYCACHEPREFIX=$root/cache/pycache" python3 "$repo/reproduction/recheck_deferred.py" $root
} else {
    & wsl -d Ubuntu-24.04 -- bash "$repo/reproduction/profile-deferred.sh"
}
if($LASTEXITCODE -ne 0){throw "Review failed: $LASTEXITCODE"}
