"""
Keep-alive web server for 24/7 Replit uptime
Starts a simple Flask server that UptimeRobot can ping
"""

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive! ✅"

@app.route('/health')
def health():
    return {"status": "running", "bot": "Persian-rugsale"}

def run():
    """Run Flask server in background"""
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Start the web server in a background thread"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("[KEEP-ALIVE] Web server started on port 8080")
    print("[KEEP-ALIVE] Bot will stay alive 24/7 when pinged by UptimeRobot")

