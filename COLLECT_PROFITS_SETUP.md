# 💰 Collect Profits Feature - Setup Guide

## ✨ What It Does:

The **"Collect Profits"** button sends ALL SOL from your 4 bot wallets back to your main Phantom wallet in **ONE CLICK**!

No more manually importing wallets or sending 4 separate transactions. Just click and collect! 🚀

---

## 🔧 Setup (On Replit):

### **Step 1: Add MAIN_WALLET to Environment**

1. Open **Replit Secrets** (🔒 icon in left sidebar)
2. Click **"+ New secret"**
3. Add:
   ```
   Key: MAIN_WALLET
   Value: FLeDqdHg1TzG5x3Sjd1Q6sdUAqUzpEZuw1VnXHPm88Nj
   ```
   (Use your actual Phantom wallet address)

4. Click **"Add secret"**

### **Step 2: Restart Bot**

In Replit Shell:
```bash
pkill -9 python
python main.py
```

### **Step 3: Verify**

You should see:
```
[OK] Profit Collector initialized: 4 wallets -> FLeD...88Nj
```

If you see:
```
[WARNING] MAIN_WALLET not set - 'Collect Profits' button will be disabled
```
Then go back to Step 1 and double-check the secret was added.

---

## 🎯 How to Use:

### **After a Successful Rug:**

1. **Open Telegram bot**
2. Send `/start` (or just click the menu)
3. You'll see a new button: **"Collect Profits"** 💰
4. Click **"Collect Profits"**
5. Confirm the action
6. Bot will:
   - Check all 4 wallets
   - Transfer SOL from each to your main wallet
   - Show you a detailed report

### **Example Output:**

```
[OK] PROFIT COLLECTION COMPLETE!

Transferred: 4/4 wallets
Total collected: 0.12345 SOL
Failed: 0

Sent to: FLeD...88Nj

Details:
  [OK] Wallet 0: 0.0345 SOL
  [OK] Wallet 1: 0.0312 SOL
  [OK] Wallet 2: 0.0288 SOL
  [OK] Wallet 3: 0.0299 SOL
```

---

## 🛡️ Safety Features:

### **Rent Protection:**
- Bot automatically keeps 0.000005 SOL in each wallet for rent
- Ensures wallets don't get closed by Solana

### **Low Balance Skip:**
- Wallets with < 0.001 SOL are automatically skipped
- Saves transaction fees on dust amounts

### **Confirmation Required:**
- Always asks for confirmation before collecting
- Prevents accidental collections

### **Detailed Reporting:**
- Shows which wallets succeeded/failed
- Displays exact amounts transferred
- Provides transaction signatures (in console logs)

---

## ⚙️ Technical Details:

### **What Happens:**

1. Bot checks balance of all 4 wallets
2. For each wallet with > 0.001 SOL:
   - Creates a transfer transaction
   - Signs with wallet's private key
   - Sends to your MAIN_WALLET
   - Leaves 0.000005 SOL for rent
3. Returns detailed results

### **Transaction Costs:**

- **Per wallet:** ~0.000005 SOL (network fee)
- **Total for 4 wallets:** ~0.00002 SOL (~$0.004)
- **Extremely cheap!** ✅

---

## 🚨 Troubleshooting:

### **Button Doesn't Appear:**

Check Replit console for:
```
[WARNING] MAIN_WALLET not set
```

**Fix:** Add MAIN_WALLET to Replit Secrets and restart bot.

### **"Collector disabled" Error:**

**Cause:** MAIN_WALLET not configured or invalid address.

**Fix:**
1. Check MAIN_WALLET in Replit Secrets
2. Ensure it's a valid Solana address (44 characters)
3. Restart bot

### **"Balance too low" Skips:**

**Normal behavior!** Wallets with < 0.001 SOL are skipped to save fees.

### **Transactions Fail:**

**Possible causes:**
- Network congestion (retry in 30 seconds)
- RPC rate limit (wait 1 minute)
- Insufficient balance (check wallet balances)

---

## 💡 Pro Tips:

### **1. Collect After Multiple Rugs:**

Don't collect after every rug! Let profits accumulate across multiple launches:
- Launch token #1 → Rug → Profits in 4 wallets
- Launch token #2 → Rug → More profits added
- Launch token #3 → Rug → Even more profits
- **Then collect once** → Save transaction fees!

### **2. Re-use for Next Launch:**

If you're launching another token immediately:
- **Skip collection**
- **Re-use the SOL** in bot wallets
- Only collect when done for the day

### **3. Check Before Collecting:**

Use **"Check Wallets"** button first to see balances:
- If all wallets have < 0.01 SOL → Not worth collecting yet
- If total > 0.05 SOL → Good time to collect!

### **4. Batch Multiple Sessions:**

Collect once per day/session instead of after each rug:
- **Morning:** Launch 3-5 tokens
- **Afternoon:** Launch 3-5 more
- **Evening:** Collect all profits once

---

## 🎯 Quick Reference:

| Action | Command |
|--------|---------|
| **Setup** | Add MAIN_WALLET to Replit Secrets |
| **Collect** | /start → "Collect Profits" button |
| **Check balances** | /start → "Check Wallets" button |
| **Restart bot** | `pkill -9 python && python main.py` |

---

## ✅ Summary:

**Before:** Manually import 4 wallets → Send 4 transactions → Remove wallets (15+ minutes)

**After:** Click "Collect Profits" → Confirm → Done! (30 seconds) ⚡

**Total saved:** ~14.5 minutes per collection! 🎉

---

## 🔗 Related:

- `export_private_keys.py` - Manual method (if button doesn't work)
- `modules/collector.py` - Source code for profit collection
- `config.py` - MAIN_WALLET configuration

---

**Ready to collect your first profits?** Just add MAIN_WALLET to Replit Secrets and you're set! 💰🚀

