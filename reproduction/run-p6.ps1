[CmdletBinding()]
param([switch]$WithModels,[switch]$ModelsOnly,[string]$Distribution='Ubuntu-24.04',[string]$DataDirectory,[string]$CpuPlaces='{0},{2},{4},{6}')
$ErrorActionPreference='Stop'
$repoPath=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$linuxPath=(& wsl -d $Distribution -- wslpath -a $repoPath.Replace('\','/')).Trim()
if($LASTEXITCODE -ne 0 -or -not $linuxPath){throw 'Cannot resolve repository in WSL.'}
$wslArgs=@('-d',$Distribution,'--','env',"P6_OMP_PLACES=$CpuPlaces")
if($DataDirectory){
    New-Item -ItemType Directory -Force -Path $DataDirectory | Out-Null
    $dataPath=(Resolve-Path -LiteralPath $DataDirectory).Path
    $linuxData=(& wsl -d $Distribution -- wslpath -a $dataPath.Replace('\','/')).Trim()
    if($LASTEXITCODE -ne 0 -or -not $linuxData){throw 'Cannot resolve data directory in WSL.'}
    $wslArgs+="VECLUT_REPRO_DIR=$linuxData"
}
if(-not $ModelsOnly){
    $kernelArgs=$wslArgs+@('bash',"$linuxPath/reproduction/run-p6.sh")
    & wsl @kernelArgs
    if($LASTEXITCODE -ne 0){throw "P6 failed with code $LASTEXITCODE; logs preserved."}
}
if($WithModels -or $ModelsOnly){
    $modelArgs=$wslArgs+@('bash',"$linuxPath/reproduction/run-p6-models.sh")
    & wsl @modelArgs
    if($LASTEXITCODE -ne 0){throw "P6 model confirmation failed with code $LASTEXITCODE; logs preserved."}
}
