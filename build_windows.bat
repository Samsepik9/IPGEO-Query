@echo off
REM ==========================================================
REM  IPGEO-Query  一键打包 (Windows .bat)
REM  双击或在 cmd 中执行即可
REM ==========================================================
setlocal

set APP_NAME=IPGEO-Query
set SCRIPT=ip_geo_query.py

echo [1/4] 检查 Python ...
where python >nul 2>nul
if errorlevel 1 (
    echo [ERR] 未找到 python, 请先安装 Python 3.10+ 并加入 PATH
    pause & exit /b 1
)
python --version

echo [2/4] 安装/更新 PyInstaller ...
python -m pip install --upgrade pyinstaller

echo [3/4] 清理旧产物 ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APP_NAME%.spec del /q %APP_NAME%.spec
if exist __pycache__ rmdir /s /q __pycache__

echo [4/4] 打包 ...
python -m PyInstaller ^
    --clean --noconfirm ^
    --onefile --windowed ^
    --name=%APP_NAME% ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module PyQt5 --exclude-module PyQt6 ^
    --exclude-module PySide2 --exclude-module PySide6 ^
    --exclude-module wx ^
    %SCRIPT%

if exist dist\%APP_NAME%.exe (
    echo.
    echo ========================================
    echo  打包完成: dist\%APP_NAME%.exe
    echo ========================================
    explorer dist
) else (
    echo [ERR] 打包失败
)
endlocal
pause
