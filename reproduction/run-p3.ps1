[CmdletBinding()]
param([switch]$Quick, [string]$Distribution='Ubuntu-24.04', [string]$DataDirectory, [string]$CpuPlaces='{0},{2},{4},{6}')
$ErrorActionPreference='Stop'
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$linuxPath=(& wsl -d $Distribution -- wslpath -a $repoPath.Replace('\','/')).Trim()
if($LASTEXITCODE -ne 0 -or -not $linuxPath){throw 'Cannot access repository through WSL.'}
$wslArgs=@('-d',$Distribution,'--','env',"P3_OMP_PLACES=$CpuPlaces")
if($DataDirectory){
    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    $dataPath=(Resolve-Path -LiteralPath $DataDirectory).Path
    $linuxDataPath=(& wsl -d $Distribution -- wslpath -a $dataPath.Replace('\','/')).Trim()
    if($LASTEXITCODE -ne 0 -or -not $linuxDataPath){throw 'Cannot resolve data directory.'}
    $wslArgs+="VECLUT_REPRO_DIR=$linuxDataPath"
}
$wslArgs+=@('bash',"$linuxPath/reproduction/run-p3.sh")
if($Quick){$wslArgs+='--quick'}
& wsl @wslArgs
if($LASTEXITCODE -ne 0){throw "P3 failed with code $LASTEXITCODE. See printed evidence directory."}
