@echo off
REM ===========================================================================
REM  CrimeNet AI - Windows one-click start
REM  Opens the API server and the web app in two terminal windows.
REM  Requires: Python 3.11+ and Node.js 20+ on PATH.
REM ===========================================================================
setlocal
set ROOT=%~dp0

echo.
echo  CrimeNet AI - Evidence-Driven Criminal Network Reconstruction
echo  ------------------------------------------------------------
echo.

REM --- create the virtual environment on first run ---------------------------
if not exist "%ROOT%backend\.venv" (
  echo [1/4] Creating Python virtual environment...
  python -m venv "%ROOT%backend\.venv" || goto :error
  echo [2/4] Installing backend dependencies ^(this takes a few minutes once^)...
  "%ROOT%backend\.venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  "%ROOT%backend\.venv\Scripts\python.exe" -m pip install -r "%ROOT%backend\requirements.txt" || goto :error
  "%ROOT%backend\.venv\Scripts\python.exe" -m spacy download en_core_web_sm || goto :error
) else (
  echo [1/4] Virtual environment found.
  echo [2/4] Backend dependencies already installed.
)

REM --- frontend dependencies --------------------------------------------------
if not exist "%ROOT%frontend\node_modules" (
  echo [3/4] Installing frontend dependencies...
  pushd "%ROOT%frontend" && call npm install || goto :error
  popd
) else (
  echo [3/4] Frontend dependencies already installed.
)

REM --- start both services ----------------------------------------------------
echo [4/4] Starting services...
start "CrimeNet API :8000" cmd /k ""%ROOT%backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 4 /nobreak >nul
start "CrimeNet Web :5173" cmd /k "cd /d "%ROOT%frontend" && npm run dev"
timeout /t 4 /nobreak >nul
start "" http://localhost:5173

echo.
echo  Web app : http://localhost:5173
echo  API docs: http://localhost:8000/api/docs
echo  Sign in : SUP-1100 / supervise123
echo.
echo  Close the two terminal windows to stop the services.
goto :eof

:error
echo.
echo  Startup failed. Check that Python 3.11+ and Node.js 20+ are installed and on PATH.
pause
