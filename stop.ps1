$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    $studioState = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/state' -TimeoutSec 2
    if ($studioState.type -ne 'state' -or $null -eq $studioState.settings) { throw 'Port 8080 is not Avatar Studio.' }
    Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/control' -Method Post -ContentType 'application/json' -Body '{"action":"shutdown"}' -TimeoutSec 2 | Out-Null
    Write-Output 'Avatar Studio is shutting down and releasing the camera.'
} catch { Write-Output $_.Exception.Message }
if (Test-Path -LiteralPath 'data/server.pid') { Remove-Item -LiteralPath 'data/server.pid' }
