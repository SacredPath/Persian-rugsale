# 24/7 Replit Keep-Alive Setup

## How It Works

Replit free tier stops your bot after **~1 hour of inactivity**. To prevent this:

1. Bot runs a **Flask web server** (port 8080)
2. **UptimeRobot** pings your bot every 5 minutes
3. Replit sees activity → **stays awake 24/7**

**Cost: FREE** ✅

---

## Step-by-Step Setup

### 1. Update Bot on Replit

```bash
# On Replit Shell:
git pull origin main
pip install flask
python main.py
```

You should see:
```
[KEEP-ALIVE] Web server started on port 8080
[KEEP-ALIVE] Bot will stay alive 24/7 when pinged by UptimeRobot
Simple Rug Bot Starting...
```

### 2. Get Your Replit URL

Your bot's URL is:
```
https://Persian-rugsale.watchdoggirl.repl.co
```

Test it:
- Open that URL in browser
- Should see: "Bot is alive! ✅"

### 3. Sign Up for UptimeRobot

1. Go to: **https://uptimerobot.com**
2. Click "Sign Up" (FREE account)
3. Verify email

### 4. Add Monitor

1. Click **"+ Add New Monitor"**
2. **Monitor Type:** HTTP(s)
3. **Friendly Name:** Persian Rug Bot
4. **URL:** `https://Persian-rugsale.watchdoggirl.repl.co`
5. **Monitoring Interval:** 5 minutes
6. Click **"Create Monitor"**

### 5. Verify It Works

**Wait 5-10 minutes**, then:

1. Check UptimeRobot dashboard:
   - Status should be **"Up"** (green)
   - Response time shown
   
2. Test Telegram bot:
   - Send `/start`
   - Should respond instantly

3. Come back in 24 hours:
   - Bot should still respond
   - UptimeRobot shows 99%+ uptime

---

## Troubleshooting

### Bot Still Stops

**Problem:** Replit might still stop bot

**Fix:**
- Check UptimeRobot is pinging every 5 minutes
- Verify URL is correct
- Check Replit console for errors

### "Bot is alive!" Page Not Loading

**Problem:** Flask server not running

**Fix:**
```bash
# On Replit:
pip install flask
python main.py
```
Look for `[KEEP-ALIVE] Web server started` message

### UptimeRobot Shows "Down"

**Possible Causes:**
1. Bot crashed (check Replit console)
2. Replit having issues (restart bot)
3. Network glitch (wait 5 mins, usually resolves)

---

## What UptimeRobot Does

- **Pings your bot:** Every 5 minutes
- **Monitors uptime:** Shows 99%+ if working
- **Email alerts:** If bot goes down
- **Statistics:** Response times, downtime history
- **Free tier:** Up to 50 monitors

---

## Alternative: Replit Always On (Paid)

If you want guaranteed uptime without UptimeRobot:

- **Replit Hacker Plan:** $7/month
- **Always On** feature included
- No need for keep-alive server
- More resources, faster bot

For most users, **UptimeRobot (FREE) is enough!**

---

## Summary

✅ **Install:** `pip install flask`
✅ **Your URL:** `https://Persian-rugsale.watchdoggirl.repl.co`
✅ **UptimeRobot:** Add monitor, ping every 5 mins
✅ **Result:** Bot runs 24/7 for FREE!

Done! 🎯

