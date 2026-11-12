# Invoice Extractor Launcher for PowerShell
$ProjectDir = $PSScriptRoot
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Starting Invoice Extractor (FastAPI + Streamlit)..." -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Start API
Write-Host "[1/2] Starting FastAPI Backend on port 8000..." -ForegroundColor Yellow
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectDir\api'; & '$VenvPython' -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 3

# Start UI
Write-Host "[2/2] Starting Streamlit Frontend on port 8501..." -ForegroundColor Yellow
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectDir\ui'; `$env:API_BASE_URL='http://localhost:8000'; & '$VenvPython' -m streamlit run app.py --server.port 8501"

Write-Host "====================================================" -ForegroundColor Green
Write-Host "Both servers started!" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "Web App:  http://localhost:8501" -ForegroundColor White
Write-Host "====================================================" -ForegroundColor Green
