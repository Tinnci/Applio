@echo off
setlocal
for %%F in ("%~dp0.") do set "folder_name=%%~nF"

title %folder_name% (using .venv)

if not exist .venv (
    echo Virtual environment (.venv) not found.
    echo Please run 'run-install.bat' first to set up the environment using UV.
    pause
    exit /b 1
)

echo Activating virtual environment and starting Applio...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Running Applio...
python app.py --open

echo.
echo Applio has finished or encountered an error. Press any key to close this window.
pause
