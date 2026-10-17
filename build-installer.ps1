param([string]$Compiler, [switch]$RebuildDesktop)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($RebuildDesktop) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\build-desktop.ps1"
    if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
}
if (-not (Test-Path -LiteralPath 'release-layout/AvatarStudio/AvatarStudio.exe')) {
    throw 'Build desktop first: ./build-desktop.ps1'
}
if (-not $Compiler) {
    $candidates = @("$PSScriptRoot\build\tools\InnoSetup\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe")
    $Compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Compiler) { throw 'Install Inno Setup 6, or provide -Compiler with the ISCC.exe path.' }
& $Compiler 'installer/AvatarStudio.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
$installer = Get-Item 'installers/AvatarStudio-0.8.0-Windows-x64-Setup.exe'
$hash = (Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $($installer.Name)" | Set-Content -LiteralPath ($installer.FullName + '.sha256') -Encoding ascii
Copy-Item -LiteralPath 'installer/README.txt' -Destination 'installers/安装说明.txt' -Force
Write-Output "Ready: $($installer.FullName)"
