[CmdletBinding()]
param(
    [switch]$Quick,
    [switch]$Confirm,
    [string]$Distribution = 'Ubuntu-24.04',
    [string]$DataDirectory,
    [string]$CpuPlaces = '{0},{2},{4},{6}'
)
$ErrorActionPreference = 'Stop'
if ($Quick -and $Confirm) { throw 'Choose either -Quick or -Confirm.' }
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$linuxPath = (& wsl -d $Distribution -- wslpath -a $repoPath.Replace('\', '/')).Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxPath) { throw 'Cannot access repository through WSL.' }
$wslArgs = @('-d', $Distribution, '--', 'env', "P2_OMP_PLACES=$CpuPlaces")
if ($DataDirectory) {
    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    $dataPath = (Resolve-Path -LiteralPath $DataDirectory).Path
    $linuxDataPath = (& wsl -d $Distribution -- wslpath -a $dataPath.Replace('\', '/')).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxDataPath) { throw 'Cannot resolve data directory.' }
    $wslArgs += "VECLUT_REPRO_DIR=$linuxDataPath"
}
$wslArgs += @('bash', "$linuxPath/reproduction/run-p2.sh")
if ($Quick) { $wslArgs += '--quick' }
if ($Confirm) { $wslArgs += '--confirm' }
& wsl @wslArgs
if ($LASTEXITCODE -ne 0) { throw "P2 failed, exit code $LASTEXITCODE. Inspect the printed evidence directory." }
