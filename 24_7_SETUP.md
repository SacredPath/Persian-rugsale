# 24/7 Bot Setup Guide

## Keep Your Bot Running 24/7 on Replit (FREE)

### Problem:
Replit free tier puts your bot to sleep after inactivity

### Solution:
Use UptimeRobot to ping your bot every 5 minutes

---

## Step-by-Step Setup:

### 1. Push Updates to Replit
```bash
git add .
git commit -m "Add 24/7 keep-alive support"
git push origin main
```

On Replit:
```bash
git pull origin main
pip install flask
python main.py
```

### 2. Get Your Replit URL
After running the bot, Replit will show a URL like:
```
https://your-repl-name.your-username.repl.co
```

**Copy this URL!**

### 3. Set Up UptimeRobot (FREE)

1. Go to: https://uptimerobot.com/
2. Sign up (free account)
3. Click "Add New Monitor"
4. Fill in:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** My Rug Bot
   - **URL:** `https://your-repl-name.your-username.repl.co`
   - **Monitoring Interval:** 5 minutes
5. Click "Create Monitor"

**Done!** UptimeRobot will ping your bot every 5 minutes to keep it alive.

---

## How It Works:

```
Replit Bot ← Ping every 5 min ← UptimeRobot
     ↓
Stays awake 24/7
```

1. Bot starts web server on port 8080
2. UptimeRobot pings it every 5 minutes
3. Replit thinks bot is active, doesn't put it to sleep
4. Bot runs 24/7 for FREE!

---

## Verify It's Working:

1. Open your Replit URL in browser
2. Should see: "Bot is alive!"
3. Check UptimeRobot dashboard (should be green/up)
4. Bot console should show: `[INFO] Keep-alive server started on port 8080`

---

## Alternative: Replit Always On (PAID)

If you want guaranteed uptime without UptimeRobot:

1. Go to Replit settings
2. Enable "Always On" ($20/month)
3. Bot runs 24/7 automatically

**Recommendation:** Use UptimeRobot (free) first, upgrade if needed.

---

## Troubleshooting:

### Bot still goes to sleep:
- Check UptimeRobot is pinging correctly (green status)
- Verify Replit URL is correct
- Make sure Flask installed: `pip install flask`

### "Port 8080 already in use":
- Replit is restarting, wait 30 seconds
- Or change port in `keep_alive.py` (line 13)

### UptimeRobot shows "Down":
- Bot might be crashed, check Replit console
- Restart bot on Replit
- Wait 1 minute for monitor to refresh

---

## What You Get:

✅ Bot runs 24/7 for FREE
✅ Automatic restart if crashed
✅ No manual intervention needed
✅ Email alerts from UptimeRobot if bot goes down

---

## Notes:

- Free Replit accounts have limited CPU hours (use UptimeRobot efficiently)
- If you hit limits, upgrade to Replit paid plan
- UptimeRobot free tier: up to 50 monitors, 5-min intervals
- Keep-alive server uses minimal resources

