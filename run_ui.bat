@echo off
title Invoice Extractor UI (Port 8501)
set API_BASE_URL=http://localhost:8000
cd /d "%~dp0ui"
echo =======================================================
echo Starting Streamlit UI at http://localhost:8501
echo =======================================================
"..\.venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
pause
