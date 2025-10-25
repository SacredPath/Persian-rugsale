@echo off
REM Quick GitHub deployment script for Windows
REM Run this to push to GitHub, then import to Replit

echo ================================================================
echo        GITHUB DEPLOYMENT - BYPASS REPLIT AGENTS
echo ================================================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo [INIT] Initializing Git repository...
    git init
) else (
    echo [OK] Git already initialized
)

REM Create/verify .gitignore
if not exist ".gitignore" (
    echo [CREATE] Creating .gitignore...
    (
        echo # Secrets (NEVER commit!^)
        echo .env
        echo .env.local
        echo wallets/*.json
        echo *.json
        echo replit_secrets.json
        echo.
        echo # Python
        echo __pycache__/
        echo *.pyc
        echo .pytest_cache/
        echo.
        echo # Replit
        echo .replit
        echo replit.nix
    ) > .gitignore
    echo [OK] .gitignore created
) else (
    echo [OK] .gitignore exists
)

REM Check for secrets
echo.
echo [SECURITY] Checking for secrets in Git...

git ls-files | findstr /C:".env" > nul
if %ERRORLEVEL% EQU 0 (
    echo WARNING: .env file is tracked by Git!
    echo    Run: git rm --cached .env
    exit /b 1
)

git ls-files | findstr /C:"wallets" > nul
if %ERRORLEVEL% EQU 0 (
    echo WARNING: Wallet files are tracked by Git!
    echo    Run: git rm --cached wallets/*.json
    exit /b 1
)

echo [OK] No secrets found in Git

REM Add files
echo.
echo [GIT] Adding files to Git...
git add .

REM Show status
echo.
echo [INFO] Files to be committed:
git status --short

echo.
echo [CONFIRM] These files will be pushed to GitHub.
echo           Make sure NO secrets are included!
echo.
set /p CONFIRM="Continue? (y/n): "

if /i not "%CONFIRM%"=="y" (
    echo [CANCELLED] Deployment cancelled
    exit /b 1
)

REM Commit
echo.
echo [GIT] Committing changes...
git commit -m "Deploy Solana rug bot - ready for Replit"

REM Check if remote exists
git remote get-url origin > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ================================================================
    echo NEXT STEPS:
    echo ================================================================
    echo.
    echo 1. Create GitHub repository:
    echo    * Go to: https://github.com/new
    echo    * Name: solana-rug-bot
    echo    * Private: YES (recommended^)
    echo    * Click 'Create repository'
    echo.
    echo 2. Add remote and push:
    echo    git remote add origin https://github.com/YOUR_USERNAME/solana-rug-bot.git
    echo    git branch -M main
    echo    git push -u origin main
    echo.
    echo 3. Import to Replit:
    echo    * Go to: https://replit.com
    echo    * Create Repl -^> Import from GitHub
    echo    * Enter your repo URL
    echo    * Make it PRIVATE
    echo    * Import
    echo.
    echo 4. Add Secrets in Replit:
    echo    * Click Secrets (lock icon^)
    echo    * Copy from REPLIT_SECRETS.txt
    echo    * Add all 6 secrets
    echo.
    echo 5. Click Run!
    echo.
    echo ================================================================
) else (
    echo.
    echo [GIT] Pushing to GitHub...
    git push -u origin main
    
    echo.
    echo Done! Pushed to GitHub!
    echo.
    echo NEXT: Import to Replit from your GitHub repo
)

echo.
echo Done! Git deployment complete!
pause

