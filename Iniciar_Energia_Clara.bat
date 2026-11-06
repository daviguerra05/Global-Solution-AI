@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Prepare o ambiente conforme README.md antes de iniciar.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m scripts.servicos iniciar
if errorlevel 1 (
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8501"
