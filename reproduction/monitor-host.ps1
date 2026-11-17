param([Parameter(Mandatory)][string]$OutputFile,[Parameter(Mandatory)][string]$StopFile)
$ErrorActionPreference='Stop'
while(-not (Test-Path -LiteralPath $StopFile)) {
    try {
        $sample=@{unix_ms=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); processors=@(Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation | Select-Object Name,PercentProcessorUtility,PercentofMaximumFrequency,ParkingStatus)}
        $sample | ConvertTo-Json -Depth 4 -Compress | Add-Content -LiteralPath $OutputFile -Encoding utf8
    } catch {
        @{unix_ms=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();error=$_.Exception.Message} | ConvertTo-Json -Compress | Add-Content -LiteralPath $OutputFile -Encoding utf8
    }
    Start-Sleep -Seconds 2
}
