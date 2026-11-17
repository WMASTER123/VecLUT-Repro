[CmdletBinding()]
param([switch]$Quick,[switch]$Full,[string]$Distribution='Ubuntu-24.04',[string]$DataDirectory,[string]$CpuPlaces='{0},{2},{4},{6}')
$ErrorActionPreference='Stop'
if($Quick -and $Full){throw 'Choose Quick or Full, not both.'}
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$linuxPath=(& wsl -d $Distribution -- wslpath -a $repoPath.Replace('\','/')).Trim()
if($LASTEXITCODE -ne 0 -or -not $linuxPath){throw 'Cannot resolve repository in WSL.'}
$wslArgs=@('-d',$Distribution,'--','env',"P3_OMP_PLACES=$CpuPlaces")
if($DataDirectory){
    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    $dataPath=(Resolve-Path -LiteralPath $DataDirectory).Path
    $linuxData=(& wsl -d $Distribution -- wslpath -a $dataPath.Replace('\','/')).Trim()
    if($LASTEXITCODE -ne 0 -or -not $linuxData){throw 'Cannot resolve data directory in WSL.'}
    $wslArgs+="VECLUT_REPRO_DIR=$linuxData"
}
$wslArgs+=@('bash',"$linuxPath/reproduction/run-p4.sh")
if($Quick){$wslArgs+='--quick'}
if($Full){$wslArgs+='--full'}
& wsl @wslArgs
if($LASTEXITCODE -ne 0){throw "P4 failed with code $LASTEXITCODE; logs preserved."}
