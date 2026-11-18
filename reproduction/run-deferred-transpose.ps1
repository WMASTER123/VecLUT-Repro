param([ValidateSet('all','build')][string]$Stage='all')
$ErrorActionPreference='Stop'
$script=Join-Path $PSScriptRoot 'run-deferred-transpose.sh'
$linuxScript=(& wsl -d Ubuntu-24.04 -- wslpath -a -u $script).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve WSL script path' }
& wsl -d Ubuntu-24.04 -- bash $linuxScript $Stage
if ($LASTEXITCODE -ne 0) { throw "Experiment failed: $LASTEXITCODE" }
