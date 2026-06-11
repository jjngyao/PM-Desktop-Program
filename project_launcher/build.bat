@echo off
echo ========================================
echo   Project Launcher - Build Script
echo ========================================
echo.

REM Ensure we're in the script's directory
cd /d "%~dp0"

echo [1/3] Installing PyInstaller...
pip install pyinstaller --quiet

echo [2/3] Building ProjectLauncher.exe...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name ProjectLauncher ^
  --clean ^
  --add-data "icon.png;." ^
  --hidden-import tkinter ^
  --hidden-import tkinter.ttk ^
  --hidden-import tkinter.filedialog ^
  --hidden-import tkinter.messagebox ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo BUILD FAILED! Check errors above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Build complete!
echo.
echo Executable: dist\ProjectLauncher.exe
echo.
echo You can copy dist\ProjectLauncher.exe anywhere and run it.
echo.

REM Optionally open the dist folder
explorer dist

pause
