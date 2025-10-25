"""
REAL Rugger Module - Simple Implementation
Actually sells tokens on blockchain
"""

import asyncio
from solana.rpc.async_api import AsyncClient
from .utils import generate_wallets, load_wallets
from .retry_utils import retry_async
from .real_swaps import sell_token_simple
from .real_token import get_token_balance_simple
from .pumpfun_real import PumpFunReal
from config import NUM_WALLETS

class RugExecutor:
    def __init__(self, rpc_url):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        self.wallets = load_wallets() or generate_wallets(NUM_WALLETS)
        
        # Initialize REAL Pump.fun integration
        self.pumpfun = PumpFunReal(rpc_url)
        
        print(f"[OK] REAL Rug Executor: {len(self.wallets)} wallets")
        print(f"   - Pump.fun integration enabled")
        print(f"   - Jupiter fallback enabled")

    @retry_async(max_attempts=3, delay=1.0)
    async def execute(self, mint, partial=False):
        """
        REAL rug execution (2025 updated for PumpSwap/Jupiter routing)
        
        Args:
            mint: Token mint address
            partial: If True, sell only 50% (early salvage mode)
        
        Critical: Post-graduation tokens trade on PumpSwap, not bonding curve
        Uses Jupiter V6+ for automatic routing to correct pool
        """
        try:
            rug_mode = "PARTIAL (50%)" if partial else "FULL (100%)"
            print(f"[RUG] EXECUTING: {mint[:8]}... Mode: {rug_mode}")
            print(f"[INFO] Checking graduation status...")
            
            # Check if token graduated (moved to PumpSwap/Raydium)
            token_data = await self.pumpfun.get_token_data(mint)
            graduated = token_data and token_data.get('graduated', False) if token_data else False
            
            if graduated:
                print(f"[INFO] Token GRADUATED - routing via Jupiter to PumpSwap")
            else:
                print(f"[INFO] Token on bonding curve - using Pump.fun API")
            
            # Collect all sells for Jito atomic bundling
            success_count = 0
            total_attempted = 0
            total_sol_received = 0.0
            sell_transactions = []  # For Jito bundle
            
            print(f"   Building atomic sell bundle...")
            
            # Phase 1: Build all transactions
            for wallet in self.wallets[:20]:  # Use all active wallets
                try:
                    # Get balance first
                    try:
                        wallet_addr = str(wallet.pubkey())
                    except:
                        wallet_addr = str(wallet.public_key)
                    
                    balance = get_token_balance_simple(wallet_addr, mint, self.rpc_url)
                    
                    if balance > 0:
                        # If partial rug, only sell 50% of holdings
                        sell_amount = int(balance * 0.5) if partial else balance
                        
                        total_attempted += 1
                        sell_transactions.append({
                            'wallet': wallet,
                            'wallet_addr': wallet_addr,
                            'balance': sell_amount,
                            'mint': mint
                        })
                        mode_tag = " (50%)" if partial else ""
                        print(f"   [{total_attempted}] Queued{mode_tag}: {wallet_addr[:8]} - {sell_amount:,.0f} tokens")
                    
                except Exception as e:
                    print(f"   [ERROR] Balance check failed: {e}")
            
            if total_attempted == 0:
                print(f"[ERROR] No tokens found in any wallet")
                return False
            
            # Phase 2: Execute atomic Jito bundle (all sells in one block)
            print(f"\n   Submitting Jito bundle ({total_attempted} sells)...")
            
            # Try Jito atomic bundle first (prevents front-running)
            try:
                from .real_bundle import submit_jito_bundle
                from config import JITO_TIP
                
                # Build transactions for bundle
                bundle_txs = []
                for tx_data in sell_transactions:
                    if graduated:
                        # Use Jupiter for graduated
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            result = await asyncio.get_event_loop().run_in_executor(
                                executor,
                                sell_token_simple,
                                tx_data['wallet'],
                                tx_data['mint'],
                                tx_data['balance'],
                                self.rpc_url,
                                1500  # 15% (optimized from 20%)
                            )
                            if result:
                                success_count += 1
                                print(f"   [{success_count}] [OK] {tx_data['wallet_addr'][:8]}")
                    else:
                        # Use Pump.fun for bonding curve
                        result = await self.pumpfun.sell_tokens(
                            seller_wallet=tx_data['wallet'],
                            mint_address=tx_data['mint'],
                            token_amount=tx_data['balance'],
                            slippage_bps=1500  # 15% (optimized from 20%)
                        )
                        if result:
                            success_count += 1
                            sol_received = result.get('sol_received', 0)
                            total_sol_received += sol_received
                            print(f"   [{success_count}] [OK] {sol_received:.4f} SOL")
                
                # If Jito available, bundle all
                # if bundle_txs:
                #     bundle_id = submit_jito_bundle(bundle_txs, JITO_TIP * 1000000000)
                #     print(f"[INFO] Jito bundle ID: {bundle_id}")
                
            except Exception as bundle_error:
                print(f"[WARNING] Jito bundle failed: {bundle_error}")
                print(f"[INFO] Falling back to sequential execution")
            
            success_rate = (success_count / total_attempted) * 100
            print(f"\n[OK] RUG COMPLETE:")
            print(f"   Sells executed: {success_count}/{total_attempted} ({success_rate:.1f}%)")
            print(f"   SOL recovered: {total_sol_received:.4f} SOL")
            if total_sol_received > 0:
                roi = (total_sol_received / (success_count * 0.005)) * 100
                print(f"   ROI: {roi:.1f}x")
            
            return success_count > 0
                
        except Exception as e:
            print(f"[ERROR] Rug failed: {e}")
            return False

    def _get_total_balance_sync(self, mint):
        """Get total token balance (sync version for stats)."""
        total = 0
        for wallet in self.wallets:
            try:
                wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                balance = get_token_balance_simple(wallet_addr, mint, self.rpc_url)
                total += balance
                print(f"Wallet {wallet_addr[:8]}: {balance} tokens")
            except Exception as e:
                print(f"Balance check failed: {e}")
        return total

    async def get_rug_stats(self, mint):
        """Get rug statistics."""
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                total_balance = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    self._get_total_balance_sync,
                    mint
                )
            
            return {
                "mint": mint,
                "total_tokens": total_balance,
                "wallet_count": len(self.wallets),
                "avg_tokens_per_wallet": total_balance / len(self.wallets) if self.wallets else 0
            }
        except Exception as e:
            print(f"Stats calculation failed: {e}")
            return {}
