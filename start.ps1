param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$studioUrl = 'http://127.0.0.1:8080'
try {
    $existing = Invoke-RestMethod -Uri "$studioUrl/api/state" -TimeoutSec 2
    if ($existing.type -eq 'state' -and $null -ne $existing.settings) {
        if (-not $NoBrowser) { Start-Process $studioUrl }
        exit 0
    }
} catch {}
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    & uv sync --python 3.11
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
}
& '.venv/Scripts/python.exe' setup_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Asset download failed. Check your connection and retry.' }
if (-not (Test-Path -LiteralPath 'dist/index.html')) {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'JavaScript dependency installation failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
}
New-Item -ItemType Directory -Path data -Force | Out-Null
$studioPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$studioScript = Join-Path $PSScriptRoot 'studio.py'
$studioProcess = Start-Process -FilePath $studioPython -ArgumentList @('-u', ('"' + $studioScript + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'data/server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'data/server-error.log')
$studioProcess.Id | Set-Content -LiteralPath 'data/server.pid'
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    Start-Sleep -Milliseconds 500
    if ($studioProcess.HasExited) { throw 'Local service failed. See data/server-error.log.' }
    try {
        $health = Invoke-RestMethod -Uri "$studioUrl/api/state" -TimeoutSec 1
        if ($health.type -eq 'state') { if (-not $NoBrowser) { Start-Process $studioUrl }; exit 0 }
    } catch {}
}
throw 'Startup timed out. See data/server-error.log.'
