# 🛑 Fix Telegram Bot Conflict (Error 409)

## Error Message:
```
Error code: 409. Description: Conflict: terminated by other getUpdates request
```

## Cause:
Multiple bot instances are running simultaneously. Telegram only allows ONE bot instance per token.

---

## ✅ SOLUTION (On Replit):

### **Step 1: Kill All Python Processes**
In Replit Shell, run:
```bash
pkill -9 python
```

Wait 5 seconds, then verify:
```bash
ps aux | grep python
```
(Should show no running python processes)

### **Step 2: Clean Restart**
```bash
python main.py
```

---

## 🔍 **If Still Getting 409 Error:**

### **Option A: Webhook Cleanup**
Sometimes old webhooks persist. Run this one-time cleanup:

```python
# Create cleanup.py
import telebot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Delete webhook (if any)
bot.delete_webhook()
print("✅ Webhook cleared!")

# Get bot info
info = bot.get_me()
print(f"✅ Bot active: @{info.username}")
```

Run it:
```bash
python cleanup.py
rm cleanup.py  # Delete after use
python main.py  # Restart bot
```

### **Option B: Restart Replit Environment**
1. Click **Stop** button in Replit
2. Wait 10 seconds
3. Click **Run** button again

### **Option C: Check Other Devices**
- Make sure you're not running the bot on your local machine
- Check if bot is running on other Replit tabs
- Close all duplicate browser tabs with this Repl

---

## 🚀 **Proper Start Procedure:**

1. **Always kill old processes first:**
   ```bash
   pkill -9 python
   sleep 2
   ```

2. **Then start fresh:**
   ```bash
   python main.py
   ```

3. **Verify startup:**
   - Should see: `[KEEP-ALIVE] Web server started on port 8080`
   - Should see: `Simple Rug Bot Starting...`
   - Should NOT see error 409

---

## 🔧 **Prevention Tips:**

1. **Use Replit's STOP button** before restarting (don't just click Run again)
2. **Close duplicate tabs** - don't open the same Repl multiple times
3. **Don't run locally AND on Replit simultaneously**
4. **If you edit code**, stop the bot first, then restart

---

## ⚠️ **Still Having Issues?**

Try this nuclear option:
```bash
# Kill everything
pkill -9 python
sleep 5

# Verify clean state
ps aux | grep python
# (Should show nothing or just the grep command itself)

# Fresh start
python main.py
```

If you STILL get 409, wait 60 seconds (Telegram's rate limit cooldown) then try again.

---

## 📊 **How to Check If Bot Is Running:**

```bash
# Check for python processes
ps aux | grep main.py

# Check if port 8080 is in use
lsof -i :8080

# Check bot status in Telegram
# Send /start - if it responds, bot is running somewhere
```

---

## ✅ **Success Indicators:**

You'll know the bot started correctly when you see:
```
[KEEP-ALIVE] Web server started on port 8080
[KEEP-ALIVE] Bot will stay alive 24/7 when pinged by UptimeRobot
Simple Rug Bot Starting...
[OK] REAL Bundler initialized:
   - 4 wallets loaded
[OK] Hype Monitor initialized with 4 wallets
[OK] REAL Rug Executor: 4 wallets
```

No error 409 = SUCCESS! 🎉

