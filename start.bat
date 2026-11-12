@echo off
title Invoice Extractor Launcher
cd /d "%~dp0"
echo Starting API and UI...
start "Invoice Extractor API" cmd.exe /c "run_api.bat"
timeout /t 3 /nobreak >nul
start "Invoice Extractor UI" cmd.exe /c "run_ui.bat"
