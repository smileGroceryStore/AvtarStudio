@echo off
cd /d "%~dp0"
if exist "%~dp0release-layout\AvatarStudio\AvatarStudio.exe" (
  start "" "%~dp0release-layout\AvatarStudio\AvatarStudio.exe"
) else if exist "%~dp0release-hud\AvatarStudio\AvatarStudio.exe" (
  start "" "%~dp0release-hud\AvatarStudio\AvatarStudio.exe"
) else if exist "%~dp0release\AvatarStudio\AvatarStudio.exe" (
  start "" "%~dp0release\AvatarStudio\AvatarStudio.exe"
) else (
  uv run --extra desktop python desktop.py
)
