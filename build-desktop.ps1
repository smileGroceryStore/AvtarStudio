$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& uv sync --extra desktop --group build
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
& '.venv/Scripts/python.exe' setup_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Asset download failed.' }
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
& '.venv/Scripts/python.exe' -m PyInstaller AvatarStudio.spec --distpath release-layout --workpath build/desktop-2d --noconfirm
if ($LASTEXITCODE -ne 0) { throw 'Desktop packaging failed.' }
& '.venv/Scripts/python.exe' scripts/package_release.py
if ($LASTEXITCODE -ne 0) { throw 'Release documentation preparation failed.' }
Write-Output 'Ready: release-layout/AvatarStudio/AvatarStudio.exe'
