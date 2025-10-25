# Replit CLI Deployment Guide

**Why CLI:** Bypass Replit Agents, direct control, faster deployment

---

## 🚀 Method 1: Replit CLI (Recommended)

### **Step 1: Install Replit CLI**

**On Windows (PowerShell):**
```powershell
# Install via npm
npm install -g @replit/cli

# OR download from GitHub
# https://github.com/replit/cli/releases
```

**On Mac/Linux:**
```bash
curl -fsSL https://replit.com/install.sh | sh
```

**Verify installation:**
```bash
replit --version
```

---

### **Step 2: Authenticate**

```bash
# Login to Replit
replit auth login

# This opens browser for authentication
# OR use token method (see below)
```

**Alternative: Use Auth Token**
```bash
# Get token from: https://replit.com/account
# Click "Generate API token"

# Set token
export REPLIT_TOKEN=your_token_here

# Windows PowerShell:
$env:REPLIT_TOKEN="your_token_here"
```

---

### **Step 3: Initialize Repl**

In your project directory:

```bash
cd solana-rug-scaffold

# Initialize new Repl
replit init

# Follow prompts:
# Name: solana-rug-bot
# Language: Python
# Public: No (private)
```

---

### **Step 4: Configure Secrets via CLI**

```bash
# Add secrets one by one
replit secrets set SOLANA_RPC "https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1"

replit secrets set HELIUS_API_KEY "4d72947c-31b4-4821-8b7b-cef17cd1eba1"

replit secrets set SHYFT_API_KEY "V4KK_GYrAApRPmJA"

replit secrets set TELEGRAM_TOKEN "8247389997:AAHgmqHyP2dEuBdgfnaqsKLSG1bhKmStRHg"

replit secrets set TELEGRAM_CHAT_ID "1318100118"

replit secrets set PROBE_MODE "false"
```

**Verify secrets:**
```bash
replit secrets list
```

---

### **Step 5: Deploy**

```bash
# Deploy to Replit
replit deploy

# OR just push code
replit push
```

---

### **Step 6: Start Bot**

```bash
# Start the Repl
replit run

# OR connect to shell
replit shell
python main.py
```

---

## 🔧 Method 2: Git + Replit Import (Easiest)

If CLI doesn't work, use Git:

### **Step 1: Create GitHub Repo**

```bash
cd solana-rug-scaffold

# Initialize git
git init

# Create .gitignore (IMPORTANT - don't commit secrets!)
echo ".env" >> .gitignore
echo "wallets/*.json" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Add files
git add .

# Commit
git commit -m "Initial commit - Solana bot"

# Create repo on GitHub.com (web interface)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/solana-rug-bot.git
git branch -M main
git push -u origin main
```

### **Step 2: Import to Replit**

1. Go to https://replit.com
2. Click "Create Repl"
3. Select "Import from GitHub"
4. Enter your repo URL
5. Make it **Private**
6. Click "Import from GitHub"

### **Step 3: Configure Secrets in Web UI**

Since code is uploaded, just add secrets:

1. Click Secrets (🔒)
2. Add 6 secrets from `REPLIT_SECRETS.txt`
3. Click Run

---

## 🛠️ Method 3: Replit CLI with Bulk Secrets

Create secrets file and upload all at once:

### **Create secrets.json:**

```bash
# In project root
cat > replit_secrets.json << 'EOF'
{
  "SOLANA_RPC": "https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1",
  "HELIUS_API_KEY": "4d72947c-31b4-4821-8b7b-cef17cd1eba1",
  "SHYFT_API_KEY": "V4KK_GYrAApRPmJA",
  "TELEGRAM_TOKEN": "8247389997:AAHgmqHyP2dEuBdgfnaqsKLSG1bhKmStRHg",
  "TELEGRAM_CHAT_ID": "1318100118",
  "PROBE_MODE": "false"
}
EOF
```

### **Upload secrets:**

```bash
# Use jq to parse and upload
cat replit_secrets.json | jq -r 'to_entries[] | "replit secrets set \(.key) \"\(.value)\""' | bash

# Then delete the file (security)
rm replit_secrets.json
```

---

## 📦 Method 4: Direct Upload via Replit API

Use curl to upload directly:

### **Get Auth Token:**

1. Go to https://replit.com/account
2. Generate API token
3. Copy token

### **Create Repl via API:**

```bash
# Set token
TOKEN="your_replit_token"

# Create Repl
curl -X POST https://replit.com/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "mutation CreateRepl($title: String!, $language: String!) { createRepl(title: $title, language: $language) { id, url } }",
    "variables": {
      "title": "solana-rug-bot",
      "language": "python3"
    }
  }'
```

### **Upload Files via API:**

```bash
# Get Repl ID from previous response
REPL_ID="your_repl_id"

# Upload files (one by one)
# This is complex - use CLI or Git instead
```

---

## ✅ Recommended Approach (Fastest)

**For you, I recommend Method 2 (Git + Import):**

1. **Why:** Easiest, no CLI setup needed
2. **Steps:**
   - Push code to GitHub (5 mins)
   - Import to Replit from GitHub (2 mins)
   - Add secrets via web UI (2 mins)
   - Click Run (1 min)
3. **Total:** 10 minutes

---

## 🔒 Security Best Practices

### **NEVER commit these to Git:**

```gitignore
# Add to .gitignore
.env
wallets/*.json
*.pyc
__pycache__/
.replit
replit_secrets.json
```

### **After pushing to GitHub:**

```bash
# Check what's in Git
git ls-files

# Should NOT see:
# - .env
# - wallets/*.json
# - Any secrets

# If accidentally committed:
git rm --cached .env
git rm --cached wallets/*.json
git commit -m "Remove secrets"
git push --force
```

---

## 🐛 Troubleshooting CLI

### "replit: command not found"

**Fix:**
```bash
# Add to PATH
export PATH="$HOME/.replit/bin:$PATH"

# Windows:
$env:PATH += ";C:\Users\YourName\.replit\bin"
```

### "Authentication failed"

**Fix:**
```bash
# Logout and re-login
replit auth logout
replit auth login

# OR use token
replit auth token YOUR_TOKEN
```

### "Permission denied"

**Fix:**
```bash
# Make executable (Mac/Linux)
chmod +x $(which replit)
```

### "Cannot initialize Repl"

**Fix:**
```bash
# Create .replit file first
cat > .replit << 'EOF'
run = "python main.py"
entrypoint = "main.py"
EOF

# Then init
replit init
```

---

## 📝 Complete CLI Script

Here's a complete script to deploy via CLI:

```bash
#!/bin/bash

# 1. Install Replit CLI (if not installed)
if ! command -v replit &> /dev/null; then
    echo "Installing Replit CLI..."
    npm install -g @replit/cli
fi

# 2. Login
echo "Logging in to Replit..."
replit auth login

# 3. Initialize Repl
echo "Initializing Repl..."
cd solana-rug-scaffold
replit init

# 4. Set secrets
echo "Setting secrets..."
replit secrets set SOLANA_RPC "https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1"
replit secrets set HELIUS_API_KEY "4d72947c-31b4-4821-8b7b-cef17cd1eba1"
replit secrets set SHYFT_API_KEY "V4KK_GYrAApRPmJA"
replit secrets set TELEGRAM_TOKEN "8247389997:AAHgmqHyP2dEuBdgfnaqsKLSG1bhKmStRHg"
replit secrets set TELEGRAM_CHAT_ID "1318100118"
replit secrets set PROBE_MODE "false"

# 5. Deploy
echo "Deploying..."
replit deploy

# 6. Start
echo "Starting bot..."
replit run

echo "✅ Deployment complete!"
echo "Test in Telegram: /start"
```

---

## 🎯 Final Recommendation

**Given Replit's new Agents interfering:**

**Use Method 2 (Git + Import)** because:
- ✅ No CLI installation needed
- ✅ Bypass Agents completely
- ✅ Full control over files
- ✅ Easy to update (git push)
- ✅ Works reliably

**Steps:**
1. Push to GitHub (2 mins)
2. Import from GitHub on Replit (1 min)
3. Add secrets via web (2 mins)
4. Run (1 min)

Total: ~6 minutes, no Agents!

---

**Need help with any method?** Let me know which you prefer!

