@echo off
REM Fix authentication for GitHub push

echo ========================================
echo Fix Authentication Issue
echo ========================================
echo.
echo You're logged in as: shsakib0002
echo But need to push to: fkoff002-glitch
echo.

cd /d "%~dp0"

echo Step 1: Updating remote URL...
git remote set-url origin https://fkoff002-glitch@github.com/fkoff002-glitch/rf-automations.git
echo Remote URL updated.
echo.

echo Step 2: Clearing cached credentials...
git credential reject https://github.com 2>nul
echo Credentials cleared.
echo.

echo Step 3: Ready to push...
echo.
echo You will be prompted for credentials:
echo - Username: fkoff002-glitch
echo - Password: Use Personal Access Token (NOT your password!)
echo.
echo Create token at: https://github.com/settings/tokens
echo.
pause

echo.
echo Pushing to GitHub...
git push -u origin main

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo SUCCESS! Code pushed!
    echo Repository: https://github.com/fkoff002-glitch/rf-automations
) else (
    echo.
    echo Authentication failed.
    echo.
    echo Make sure:
    echo 1. You have a Personal Access Token
    echo 2. Token has 'repo' scope
    echo 3. You're using the token as password (not GitHub password)
    echo.
    echo Create token: https://github.com/settings/tokens
)
echo ========================================
pause
