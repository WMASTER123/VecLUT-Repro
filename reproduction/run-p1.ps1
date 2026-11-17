[CmdletBinding()]
param(
    [switch]$WithBaseline,
    [switch]$Sanitize,
    [string]$Distribution = 'Ubuntu-24.04',
    [string]$DataDirectory
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$linuxPath = (& wsl -d $Distribution -- wslpath -a $repoPath.Replace('\', '/')).Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxPath) { throw 'Cannot access repository through WSL.' }
$sanMode = if ($Sanitize) { 'ON' } else { 'OFF' }
$wslArgs = @('-d', $Distribution, '--', 'env', "P1_SANITIZE=$sanMode")
if ($DataDirectory) {
    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    $dataPath = (Resolve-Path -LiteralPath $DataDirectory).Path
    $linuxDataPath = (& wsl -d $Distribution -- wslpath -a $dataPath.Replace('\', '/')).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxDataPath) { throw 'Cannot resolve data directory.' }
    $wslArgs += "VECLUT_REPRO_DIR=$linuxDataPath"
}
$wslArgs += @('bash', "$linuxPath/reproduction/run-p1.sh")
if ($WithBaseline) { $wslArgs += '--with-baseline' }
& wsl @wslArgs
if ($LASTEXITCODE -ne 0) { throw "P1 failed, exit code $LASTEXITCODE. Inspect the printed evidence directory." }
