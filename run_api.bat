@echo off
title Invoice Extractor API (Port 8000)
cd /d "%~dp0api"
echo =======================================================
echo Starting FastAPI Backend at http://localhost:8000
echo Swagger Docs: http://localhost:8000/docs
echo =======================================================
"..\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
