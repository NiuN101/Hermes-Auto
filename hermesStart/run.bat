@echo off
REM 双击运行 hermesStart
REM 优先用项目级 venv，没有就退到系统 Python

setlocal
cd /d "%~dp0"

set "PY=python"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"

%PY% hermesStart.py %*
endlocal
