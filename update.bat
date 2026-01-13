@echo off
title LEGO Auditor Manager
set PROJECT_DIR=C:\github\stockchecker

:: Move to the project directory
cd /d %PROJECT_DIR%

:menu
cls
echo ==========================================
echo       LEGO MASTER AUDITOR MANAGER
echo ==========================================
echo PROJECT: %PROJECT_DIR%
echo.
echo 1. Run App Locally (Streamlit)
echo 2. Upload Changes to GitHub (Add/Commit/Push)
echo 3. Check Git Status
echo 4. Exit
echo.
set /p choice="Select an option (1-4): "

if "%choice%"=="1" goto run_app
if "%choice%"=="2" goto push_git
if "%choice%"=="3" goto status_git
if "%choice%"=="4" exit

:run_app
echo.
echo Launching Streamlit...
streamlit run app.py
pause
goto menu

:push_git
echo.
echo Checking for updates from GitHub first...
git pull origin main --rebase
echo.
set /p msg="Enter a brief description of your changes: "
git add .
git commit -m "%msg%"
git push origin main
echo.
echo Done! Changes synced and sent to GitHub.
pause
goto menu

:status_git
echo.
git status
pause
goto menu