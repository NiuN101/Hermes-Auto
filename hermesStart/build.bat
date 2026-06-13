@echo off
REM Build hermesStart into a single-file Windows exe.
REM Output: hermesStart\dist\hermesStart.exe
REM
REM IMPORTANT: this script force-cleans dist/ and build/ before each run
REM to prevent leaking any personal config (e.g. a stale dist\config\
REM app_config.json that would ship your WSL username and install paths).

setlocal EnableExtensions

REM Resolve the script directory into an absolute path, robust to spaces.
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
echo [INFO] Script dir: %SCRIPT_DIR%

REM ---- 1. Check / install PyInstaller ----
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] Installing PyInstaller from Tsinghua mirror...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check Python / pip environment.
        exit /b 1
    )
)

REM ---- 2. Force-clean previous artifacts (CRITICAL) ----
if exist "%SCRIPT_DIR%\build" rmdir /s /q "%SCRIPT_DIR%\build"
if exist "%SCRIPT_DIR%\dist" rmdir /s /q "%SCRIPT_DIR%\dist"

REM ---- 3. Build ----
REM No --add-data: only collect imported Python modules.
REM --noconfirm: do not prompt to overwrite.
cd /d "%SCRIPT_DIR%"
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name hermesStart ^
  --icon "assets\hermes.ico" ^
  --collect-submodules tkinter ^
  hermesStart.py

if errorlevel 1 (
    echo [ERROR] PyInstaller failed. See log above.
    exit /b 1
)

REM ---- 4. Verify: dist/ must contain ONLY hermesStart.exe ----
set "LEAKED=0"
if exist "%SCRIPT_DIR%\dist\config" (
    echo [WARN] dist\config\ exists. Personal info may have leaked.
    set "LEAKED=1"
)
for %%f in ("%SCRIPT_DIR%\dist\*.json" "%SCRIPT_DIR%\dist\*.yaml" "%SCRIPT_DIR%\dist\*.yml" "%SCRIPT_DIR%\dist\*.txt") do (
    if exist "%%f" (
        echo [WARN] Stray data file in dist\: %%f
        set "LEAKED=1"
    )
)

echo.
if "%LEAKED%"=="1" (
    echo [WARN] Build finished but suspicious artifacts detected. Inspect dist\ manually!
) else (
    echo [DONE] Output: hermesStart\dist\hermesStart.exe
    echo        Double-click to run. If SmartScreen blocks, choose "Run anyway".
    echo        Verified: dist\ contains only hermesStart.exe, no personal info.
)
endlocal
