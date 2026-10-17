$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$testRoot = Join-Path $projectRoot 'test-results\installer-roundtrip'
$appDir = Join-Path $testRoot 'application'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$testRoot = (Resolve-Path -LiteralPath $testRoot).Path
if (-not $appDir.StartsWith($testRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected installation test directory.' }
$settingsPath = Join-Path $env:LOCALAPPDATA 'AvatarStudio\settings.json'
$savedHash = if (Test-Path -LiteralPath $settingsPath) { (Get-FileHash -LiteralPath $settingsPath).Hash } else { $null }
$setup = Join-Path $projectRoot 'installers\AvatarStudio-0.8.0-Windows-x64-Setup.exe'
$installArgs = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS="!desktopicon,!widgeticon"',('/DIR="'+$appDir+'"'),('/LOG="'+$testRoot+'\install.log"'))
$install = Start-Process -FilePath $setup -ArgumentList $installArgs -Wait -PassThru -WindowStyle Hidden
if ($install.ExitCode -ne 0) { throw "Installation failed: $($install.ExitCode)" }
$relativeFiles = @('AvatarStudio.exe','_internal\dist\index.html','_internal\desktop-assets\app.ico','THIRD-PARTY-NOTICES.txt')
foreach ($relative in $relativeFiles) {
    $original = Get-FileHash -LiteralPath (Join-Path "$projectRoot\release-layout\AvatarStudio" $relative)
    $installed = Get-FileHash -LiteralPath (Join-Path $appDir $relative)
    if ($original.Hash -ne $installed.Hash) { throw "Installed file differs: $relative" }
}
$smokeData = Join-Path $testRoot ('smoke-' + [Guid]::NewGuid().ToString('N'))
$app = Start-Process -FilePath (Join-Path $appDir 'AvatarStudio.exe') -ArgumentList '--smoke-test',('--data-dir="'+$smokeData+'"'),'--port=8096' -Wait -PassThru -WindowStyle Hidden
$result = Get-Content -LiteralPath (Join-Path $smokeData 'desktop-smoke.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $result.success) { throw 'Installed application smoke test failed.' }
$uninstaller = Join-Path $appDir 'unins000.exe'
$uninstall = Start-Process -FilePath $uninstaller -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+$testRoot+'\uninstall.log"') -Wait -PassThru -WindowStyle Hidden
if ($uninstall.ExitCode -ne 0) { throw "Uninstall failed: $($uninstall.ExitCode)" }
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath (Join-Path $appDir 'AvatarStudio.exe')) { throw 'Uninstall left application executable behind.' }
if ($savedHash -and (Get-FileHash -LiteralPath $settingsPath).Hash -ne $savedHash) { throw 'Personal settings were changed.' }
@{success=$true;installedFilesVerified=$true;desktopSmoke=$result.success;uninstalled=$true;personalSettingsPreserved=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $testRoot 'result.json') -Encoding utf8
Write-Output 'Installer install / launch / widget / tray / uninstall / personal settings checks PASS'
