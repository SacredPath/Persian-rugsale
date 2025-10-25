#!/bin/bash

# Quick GitHub deployment script
# Run this to push to GitHub, then import to Replit

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       GITHUB DEPLOYMENT - BYPASS REPLIT AGENTS            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "[INIT] Initializing Git repository..."
    git init
else
    echo "[OK] Git already initialized"
fi

# Create/verify .gitignore
if [ ! -f ".gitignore" ]; then
    echo "[CREATE] Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Secrets (NEVER commit!)
.env
.env.local
wallets/*.json
*.json
replit_secrets.json

# Python
__pycache__/
*.pyc
.pytest_cache/

# Replit
.replit
replit.nix
EOF
    echo "[OK] .gitignore created"
else
    echo "[OK] .gitignore exists"
fi

# Check for secrets in staged files
echo ""
echo "[SECURITY] Checking for secrets in Git..."

if git ls-files | grep -q ".env"; then
    echo "⚠️  WARNING: .env file is tracked by Git!"
    echo "   Run: git rm --cached .env"
    exit 1
fi

if git ls-files | grep -q "wallets/.*\.json"; then
    echo "⚠️  WARNING: Wallet files are tracked by Git!"
    echo "   Run: git rm --cached wallets/*.json"
    exit 1
fi

echo "[OK] No secrets found in Git"

# Add files
echo ""
echo "[GIT] Adding files to Git..."
git add .

# Show what will be committed
echo ""
echo "[INFO] Files to be committed:"
git status --short

echo ""
echo "[CONFIRM] These files will be pushed to GitHub."
echo "          Make sure NO secrets are included!"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[CANCELLED] Deployment cancelled"
    exit 1
fi

# Commit
echo ""
echo "[GIT] Committing changes..."
git commit -m "Deploy Solana rug bot - ready for Replit"

# Check if remote exists
if ! git remote get-url origin &> /dev/null; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "NEXT STEPS:"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "1. Create GitHub repository:"
    echo "   • Go to: https://github.com/new"
    echo "   • Name: solana-rug-bot"
    echo "   • Private: YES (recommended)"
    echo "   • Click 'Create repository'"
    echo ""
    echo "2. Add remote and push:"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/solana-rug-bot.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "3. Import to Replit:"
    echo "   • Go to: https://replit.com"
    echo "   • Create Repl → Import from GitHub"
    echo "   • Enter your repo URL"
    echo "   • Make it PRIVATE"
    echo "   • Import"
    echo ""
    echo "4. Add Secrets in Replit:"
    echo "   • Click Secrets (🔒)"
    echo "   • Copy from REPLIT_SECRETS.txt"
    echo "   • Add all 6 secrets"
    echo ""
    echo "5. Click Run!"
    echo ""
    echo "════════════════════════════════════════════════════════════"
else
    # Remote exists, push
    echo ""
    echo "[GIT] Pushing to GitHub..."
    git push -u origin main
    
    echo ""
    echo "✅ Pushed to GitHub!"
    echo ""
    echo "NEXT: Import to Replit from your GitHub repo"
fi

echo ""
echo "✅ Git deployment complete!"

