# Deploying to Replit - Complete Guide

**Why Replit:** 24/7 uptime, free tier, easy deployment, built-in secrets management

---

## 📋 Step-by-Step Deployment

### **Step 1: Create Replit Account**

1. Go to https://replit.com
2. Sign up (free account works)
3. Verify your email

---

### **Step 2: Create New Repl**

1. Click **"Create Repl"**
2. Select **"Import from GitHub"** OR **"Python"**
3. Name it: `solana-rug-bot`
4. Click **"Create Repl"**

---

### **Step 3: Upload Project Files**

**Option A: Via GitHub (Recommended)**

If you have GitHub:
```bash
# On your local machine:
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO
git push -u origin main
```

Then import in Replit from GitHub URL.

**Option B: Manual Upload**

1. In Replit, click **"Files"** panel
2. Upload these folders/files:
   - `modules/` (entire folder)
   - `wallets/` (entire folder - contains your Phantom wallet)
   - `requirements.txt`
   - `config.py`
   - `main.py`

**Files to upload:**
```
solana-rug-scaffold/
├── modules/
│   ├── __init__.py
│   ├── bundler.py
│   ├── monitor.py
│   ├── rugger.py
│   ├── utils.py
│   ├── retry_utils.py
│   ├── pumpfun_real.py
│   ├── real_swaps.py
│   ├── real_token.py
│   └── real_bundle.py
├── wallets/
│   ├── wallet_0.json (your Phantom wallet)
│   ├── wallet_1.json
│   └── ... (all wallet files)
├── requirements.txt
├── config.py
├── main.py
└── .replit (create this - see below)
```

---

### **Step 4: Configure Secrets (CRITICAL)**

**Never put API keys in code on Replit!**

1. Click **"Secrets"** (lock icon) in left sidebar
2. Add these secrets:

```
Key: SOLANA_RPC
Value: https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1

Key: HELIUS_API_KEY
Value: 4d72947c-31b4-4821-8b7b-cef17cd1eba1

Key: SHYFT_API_KEY
Value: V4KK_GYrAApRPmJA

Key: TELEGRAM_TOKEN
Value: 8247389997:AAHgmqHyP2dEuBdgfnaqsKLSG1bhKmStRHg

Key: PROBE_MODE
Value: false
```

**Important:** Replit Secrets are encrypted and not visible in code!

---

### **Step 5: Update config.py for Replit**

Modify `config.py` to read from Replit Secrets:

```python
import os
from dotenv import load_dotenv

# Load from Replit Secrets (no .env file needed)
load_dotenv()

# RPC Configuration
HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY") or os.getenv("HELIUS_API_KEY")
SHYFT_API_KEY = os.environ.get("SHYFT_API_KEY") or os.getenv("SHYFT_API_KEY")
SOLANA_RPC = os.environ.get("SOLANA_RPC") or os.getenv("SOLANA_RPC")

if SOLANA_RPC:
    RPC_URL = SOLANA_RPC
    if "devnet" in SOLANA_RPC.lower():
        print("[OK] Using DEVNET (safe for testing)")
    elif "mainnet" in SOLANA_RPC.lower():
        print("[WARNING] Using MAINNET (REAL SOL - be careful!)")
else:
    raise ValueError("[ERROR] SOLANA_RPC not configured in Replit Secrets!")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("[ERROR] TELEGRAM_TOKEN not set in Replit Secrets!")

# ... rest of config.py stays the same
```

---

### **Step 6: Create .replit File**

Create `.replit` in root directory:

```toml
run = "python main.py"
entrypoint = "main.py"
hidden = [".pythonlibs"]

[nix]
channel = "stable-23_05"

[deployment]
run = ["python", "main.py"]
deploymentTarget = "cloudrun"
```

---

### **Step 7: Update requirements.txt**

Ensure your `requirements.txt` is complete:

```txt
solana==0.30.2
pyTelegramBotAPI==4.14.0
requests==2.31.0
base58==2.1.1
python-dotenv==1.0.0
solders==0.18.1
spl-token==0.2.0
anchorpy==0.18.0
construct==2.10.68
httpx==0.23.3
```

---

### **Step 8: Install Dependencies**

In Replit Shell (bottom panel):

```bash
pip install -r requirements.txt
```

Or click **"Run"** - Replit auto-installs from requirements.txt

---

### **Step 9: Test Run**

1. Click **"Run"** button (▶️)
2. Check console for:
   ```
   [OK] Using MAINNET
   Simple Rug Bot Starting...
   ```
3. If errors, check:
   - Secrets are set correctly
   - All files uploaded
   - Dependencies installed

---

### **Step 10: Keep Bot Running 24/7**

**Option A: Replit Always-On (Paid - $7/month)**

1. Click **"Deploy"** tab
2. Enable **"Always On"**
3. Bot runs 24/7 without interruption

**Option B: UptimeRobot Ping (Free)**

Replit sleeps after inactivity. Use UptimeRobot to ping:

1. Go to https://uptimerobot.com
2. Create account (free)
3. Add New Monitor:
   - Type: **HTTP(s)**
   - URL: Your Replit URL (e.g., `https://solana-rug-bot.username.repl.co`)
   - Interval: **5 minutes**
4. UptimeRobot pings every 5 mins, keeping bot awake

**Get Replit URL:**
- Click **"Webview"** in Replit
- Copy URL
- Use in UptimeRobot

---

## 🔧 Troubleshooting

### "ModuleNotFoundError"

```bash
# In Shell:
pip install --upgrade pip
pip install -r requirements.txt
```

### "Secrets not loading"

Replit reads from `os.environ`, not `.env`:

```python
# Use this in config.py:
import os
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
```

### "Bot not responding on Telegram"

1. Check console for errors
2. Verify TELEGRAM_TOKEN in Secrets
3. Test with `/start` in Telegram
4. Check Replit isn't sleeping (use UptimeRobot)

### "Wallets not found"

```bash
# In Shell:
ls wallets/
# Should show wallet_0.json, wallet_1.json, etc.

# If missing, re-upload wallets folder
```

### "RPC errors"

1. Check SOLANA_RPC in Secrets
2. Verify Helius API key is valid
3. Test RPC:
   ```bash
   python -c "from solana.rpc.api import Client; c=Client('YOUR_RPC'); print(c.get_version())"
   ```

---

## 🔒 Security Best Practices

### **DO:**
- ✅ Use Replit Secrets for all API keys
- ✅ Set Repl to **Private** (not public)
- ✅ Never commit `.env` to GitHub
- ✅ Keep wallet files private
- ✅ Use strong Telegram bot token

### **DON'T:**
- ❌ Hardcode API keys in code
- ❌ Make Repl public
- ❌ Share Repl URL publicly
- ❌ Commit private keys to GitHub
- ❌ Use personal wallet for bot

---

## 📊 Monitoring on Replit

### **Check Bot Status**

In Replit Console, you'll see:
```
[OK] Using MAINNET
Simple Rug Bot Starting...
[OK] REAL Bundler initialized:
   - 12 wallets loaded
   - Jupiter swaps enabled
   - Jito bundles enabled
[OK] Hype Monitor initialized with 12 wallets
[OK] REAL Rug Executor: 12 wallets
```

### **View Logs**

Replit shows all `print()` statements in Console:
- Launch confirmations
- Buy/sell transactions
- Monitoring updates
- Errors

### **Check Telegram**

In your Telegram chat with the bot:
```
/start
→ Should respond: "Rug Bot Ready! Commands:..."
```

---

## 💰 Cost Comparison

| Option | Cost | Uptime | Setup |
|--------|------|--------|-------|
| **Replit Free** | $0/mo | ~12hrs/day | Easy |
| **Replit + UptimeRobot** | $0/mo | ~20hrs/day | Medium |
| **Replit Always-On** | $7/mo | 24/7 | Easy |
| **VPS (DigitalOcean)** | $6/mo | 24/7 | Hard |

**Recommendation:** Start with Free + UptimeRobot, upgrade to Always-On if successful.

---

## 🚀 Quick Start Checklist

Before clicking "Run":

- [ ] All files uploaded (modules, wallets, config, main)
- [ ] Secrets configured (5 keys)
- [ ] requirements.txt installed
- [ ] .replit file created
- [ ] Repl set to Private
- [ ] Telegram token verified
- [ ] Main wallet funded (0.05+ SOL)

---

## 📱 Using Bot on Replit

Once running, use via Telegram:

```
/start
→ Rug Bot Ready!

/launch MoonToken MOON http://image.com/logo.png
→ [LAUNCH] Creating MoonToken (MOON)...
→ [OK] Token created: 7xKXtg2...
→ [MONITOR] Auto-monitoring enabled

/status
→ Bot Status: Active tokens: 1, Wash trades: 3

/rug 7xKXtg2CW3BsC9fqzyZ9XXvGGe9fqRNjfzxkEDhVpump
→ [RUG] RUGGED! Recovered 0.15 SOL
```

---

## 🔄 Updating Bot on Replit

To update code:

1. Edit files directly in Replit
2. Click **"Stop"** (if running)
3. Click **"Run"** again
4. Bot restarts with new code

OR use GitHub sync:
1. Push changes to GitHub
2. In Replit: **Version Control** → **Pull**
3. Restart bot

---

## 📈 Scaling on Replit

**When bot is profitable:**

1. Upgrade to **Always-On** ($7/mo)
2. Add more SOL to main wallet
3. Run multiple launches per day
4. Monitor via Telegram
5. Scale to multiple bots (different Repls)

---

## ⚠️ Replit Limitations

**Be aware:**
- Free tier sleeps after 1hr inactivity
- 0.5 vCPU, 512MB RAM (sufficient for this bot)
- 1GB storage (enough for wallets + code)
- Outbound requests limited (use premium RPC)

**For high-volume operations:**
- Consider Replit Hacker plan ($7/mo)
- Or migrate to VPS (DigitalOcean, AWS)

---

## ✅ Final Deployment Steps

1. Upload all files
2. Configure Secrets
3. Install dependencies
4. Test with `/start` in Telegram
5. Run first launch with test token
6. Monitor console for errors
7. Set up UptimeRobot (optional)
8. Scale operations

---

**Status:** Ready to deploy to Replit!

**Next:** Upload files and configure Secrets, then click Run! 🚀

