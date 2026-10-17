@echo off
cd /d "%~dp0"
if exist "%~dp0release-passthrough\AvatarStudio\AvatarStudio.exe" (
  start "" "%~dp0release-passthrough\AvatarStudio\AvatarStudio.exe" --background
) else (
  uv run --extra desktop python desktop.py --background
)
