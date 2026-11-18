param([ValidateSet('All','Recheck','Diagnose','Lanes')][string]$Stage='All')
$ErrorActionPreference='Stop'
$repo=(& wsl -d Ubuntu-24.04 -- wslpath -a -u (Split-Path $PSScriptRoot)).Trim()
$root=(& wsl -d Ubuntu-24.04 -- dirname $repo).Trim()
function Check-Exit { if($LASTEXITCODE -ne 0){throw "Experiment failed: $LASTEXITCODE"} }
if($Stage -in @('All','Recheck')) {
 & wsl -d Ubuntu-24.04 -- env "PYTHONPYCACHEPREFIX=$root/cache/pycache" python3 "$repo/reproduction/recheck_deferred.py" $root; Check-Exit
}
if($Stage -in @('All','Diagnose')) {
 & wsl -d Ubuntu-24.04 -- bash "$repo/reproduction/profile-deferred.sh"; Check-Exit
}
if($Stage -in @('All','Lanes')) {
 & wsl -d Ubuntu-24.04 -- bash "$repo/reproduction/build-valid-lanes.sh"; Check-Exit
 & wsl -d Ubuntu-24.04 -- env "PYTHONPYCACHEPREFIX=$root/cache/pycache" python3 "$repo/reproduction/experiment_valid_lanes.py" $root; Check-Exit
}
