@echo off
REM 用 PyInstaller 把 hermesStart 打成单文件 exe
REM 产物：hermesStart\dist\hermesStart.exe

setlocal
cd /d "%~dp0"

REM 检查 PyInstaller，没有就装（走清华源快）
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] 装 PyInstaller（清华源）...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller
    if errorlevel 1 (
        echo [ERROR] pip install 失败，请手动检查 Python / pip 环境
        exit /b 1
    )
)

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name hermesStart ^
  --icon "assets\hermes.ico" ^
  --collect-submodules tkinter ^
  hermesStart.py

echo.
echo [DONE] 产物在 hermesStart\dist\hermesStart.exe
echo        双击它就能跑（首次启动若被 SmartScreen 拦，选"仍要运行"）
endlocal
