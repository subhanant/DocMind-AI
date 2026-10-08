@echo off
echo =============================================
echo       Starting DocuMind AI SaaS Platform     
echo =============================================
set ROOT=%~dp0
start "DocuMind AI Backend" cmd /k "cd /d %ROOT%backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 2 /nobreak >nul
start "DocuMind AI Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"
echo.
echo All services launched!
echo Frontend:  http://localhost:3000
echo Backend:   http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo =============================================
pause
