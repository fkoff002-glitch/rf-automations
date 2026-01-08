@echo off
REM Push script for rf-automations repository
REM Repository: https://github.com/fkoff002-glitch/rf-automations

echo ========================================
echo Push to GitHub Repository
echo Repository: rf-automations
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Initializing Git...
if not exist ".git" (
    git init
    echo Git initialized.
) else (
    echo Git already initialized.
)
echo.

echo Step 2: Adding all files...
git add .
echo Files added.
echo.

echo Step 3: Creating commit...
git commit -m "Initial commit: RF Automation System - Backend + Frontend"
echo Commit created.
echo.

echo Step 4: Setting remote repository...
git remote remove origin 2>nul
git remote add origin https://github.com/fkoff002-glitch/rf-automations.git
echo Remote set to: https://github.com/fkoff002-glitch/rf-automations.git
echo.

echo Step 5: Setting branch to main...
git branch -M main
echo.

echo Step 6: Pushing to GitHub...
echo.
echo You will be asked for credentials:
echo - Username: fkoff002-glitch
echo - Password: Use Personal Access Token (create at https://github.com/settings/tokens)
echo.
git push -u origin main

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS! Code pushed to GitHub!
    echo.
    echo Repository: https://github.com/fkoff002-glitch/rf-automations
    echo.
    echo Next steps:
    echo 1. Enable GitHub Pages: https://github.com/fkoff002-glitch/rf-automations/settings/pages
    echo 2. Source: main branch, Folder: /frontend
    echo 3. Frontend URL: https://fkoff002-glitch.github.io/rf-automations/
) else (
    echo Push failed. Check your credentials.
    echo Make sure you have a Personal Access Token: https://github.com/settings/tokens
)
echo ========================================
echo.
pause
