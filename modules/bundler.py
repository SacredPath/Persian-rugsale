"""
REAL Bundler Module - Simple Implementation
Uses actual blockchain transactions
"""

import requests
import asyncio
from solana.rpc.async_api import AsyncClient
from .utils import generate_wallets, load_wallets
from .retry_utils import retry_async
from .real_swaps import buy_token_simple, sell_token_simple
from .real_token import create_simple_token, get_token_balance_simple
from .pumpfun_real import PumpFunReal
from config import NUM_WALLETS, BUNDLE_SOL

class RugBundler:
    def __init__(self, rpc_url):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        # Load existing wallets
        self.wallets = load_wallets() or generate_wallets(NUM_WALLETS)
        
        # Initialize REAL Pump.fun integration
        self.pumpfun = PumpFunReal(rpc_url)
        
        print(f"[OK] REAL Bundler initialized:")
        print(f"   - {len(self.wallets)} wallets loaded")
        print(f"   - Jupiter swaps enabled")
        print(f"   - Jito bundles enabled")
        print(f"   - REAL Pump.fun integration")

    @retry_async(max_attempts=3, delay=1.0)
    async def create_token(self, name, symbol, image_url, description="Meme token on Pump.fun"):
        """Create REAL token on Pump.fun with BUNDLED initial buys (atomic via Jito)."""
        try:
            if not self.wallets:
                print("[ERROR] No wallets")
                return None
            
            print(f"[LAUNCH] Creating REAL Pump.fun token with BUNDLED buys...")
            print(f"[INFO] This will create token + do initial buys ATOMICALLY via Jito!")
            
            # Use first 3 wallets for bundled creation (1 creator + 2 buyers = 3 txs)
            # REDUCED from 4 to 3 for safer bundle size (3 txs + 1 tip = 4 total, well under 5 max)
            wallets_for_bundle = self.wallets[:3]  # Use 3 wallets total
            
            from config import BUNDLE_SOL
            print(f"[INFO] Bundle composition:")
            print(f"   - Wallet 0: Create + buy with {BUNDLE_SOL} SOL")
            print(f"   - Wallet 1-2: Buy with {BUNDLE_SOL} SOL each")
            print(f"   - Total: 3 transactions in atomic bundle (safer margin)")
            print(f"   - Total buy volume: {BUNDLE_SOL * 3} SOL")
            
            # PRE-FLIGHT: Check wallet balances BEFORE creating bundle (prevent failed txs)
            print(f"\n[PRE-FLIGHT] Checking wallet balances...")
            try:
                # Import Pubkey for balance checks
                try:
                    from solders.pubkey import Pubkey
                except ImportError:
                    from solana.publickey import PublicKey as Pubkey
                
                from config import PUMPFUN_CREATE_FEE, BUNDLE_SOL, JITO_TIP, USE_JITO_BUNDLES
                
                # Define minimum required balances
                # Only include Jito tip if bundled mode is enabled
                jito_tip_cost = JITO_TIP if USE_JITO_BUNDLES else 0.0
                creator_min = PUMPFUN_CREATE_FEE + BUNDLE_SOL + jito_tip_cost + 0.002  # Creation + buy + tip (if bundled) + buffer
                buyer_min = BUNDLE_SOL + 0.002  # Buy + buffer
                
                all_funded = True
                for i, wallet in enumerate(wallets_for_bundle):
                    wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                    wallet_pubkey = Pubkey.from_string(wallet_addr)
                    
                    balance_resp = await self.client.get_balance(wallet_pubkey)
                    balance_sol = balance_resp.value / 1e9 if balance_resp.value else 0.0
                    
                    # Determine required balance based on wallet role
                    if i == 0:
                        required_sol = creator_min
                        if USE_JITO_BUNDLES:
                            role = "Creator (create + buy + tip)"
                        else:
                            role = "Creator (create + buy, no tip)"
                    else:
                        required_sol = buyer_min
                        role = f"Buyer {i}"
                    
                    if balance_sol < required_sol:
                        print(f"   [ERROR] Wallet {i} ({role}): {balance_sol:.4f} SOL < {required_sol:.4f} SOL required")
                        print(f"           Address: {wallet_addr}")
                        print(f"           Shortfall: {required_sol - balance_sol:.4f} SOL")
                        all_funded = False
                    else:
                        surplus = balance_sol - required_sol
                        print(f"   [OK] Wallet {i} ({role}): {balance_sol:.4f} SOL (surplus: {surplus:.4f} SOL)")
                
                if not all_funded:
                    print(f"\n[ERROR] INSUFFICIENT FUNDS - Aborting token creation")
                    print(f"[INFO] Fund wallets and try again")
                    return None
                
                print(f"[OK] All wallets funded - proceeding with bundle creation\n")
                
            except Exception as balance_err:
                print(f"[WARNING] Balance check failed: {balance_err}")
                print(f"[WARNING] Proceeding anyway - ensure wallets are funded!")
            
            # Create token with bundled buys (NO API KEY NEEDED!)
            # Buy amounts determined by config.BUNDLE_SOL (e.g., 0.0075 SOL per wallet)
            mint = await self.pumpfun.create_token_bundled(
                wallets=wallets_for_bundle,
                name=name,
                symbol=symbol,
                description=description,
                image_url=image_url,
                twitter=None,
                telegram=None,
                website=None
            )
            
            if mint:
                print(f"[OK] Token created with bundled buys!")
                print(f"[INFO] Mint: {mint}")
                print(f"[INFO] All transactions submitted atomically via Jito")
                
                # Wait for Jito bundle to land
                print(f"[INFO] Waiting for Jito bundle to land on-chain...")
                await asyncio.sleep(5)  # Wait longer for bundle
                
                # Verify token exists on-chain
                print(f"[VERIFY] Checking if token exists on-chain...")
                
                try:
                    # Import Pubkey for verification
                    try:
                        from solders.pubkey import Pubkey
                    except ImportError:
                        from solana.publickey import PublicKey as Pubkey
                    
                    mint_pubkey = Pubkey.from_string(mint)
                    account_info = await self.client.get_account_info(mint_pubkey)
                    if account_info.value is None:
                        print(f"[WARNING] Token mint not yet visible on-chain")
                        print(f"[INFO] This is normal for Jito bundles - may take a few seconds")
                        print(f"[INFO] Proceeding anyway - bundle was submitted successfully")
                    else:
                        print(f"[OK] Token verified on-chain!")
                except Exception as verify_error:
                    print(f"[WARNING] Could not verify on-chain (RPC issue): {verify_error}")
                    print(f"[INFO] Proceeding anyway - bundle was submitted successfully")
                
                return mint
            else:
                print(f"[ERROR] Bundled token creation failed")
                print(f"[ERROR] Check console logs for details")
                return None
                
        except Exception as e:
            print(f"[ERROR] Token creation error: {e}")
            import traceback
            traceback.print_exc()
            return None

    @retry_async(max_attempts=5, delay=1.0)
    async def bundle_buy(self, mint, amount=None, use_jito=False):
        """
        Execute REAL buy transactions (2025 updated for organic appearance)
        Uses sequential buys with delays to avoid detection
        """
        try:
            if amount is None:
                from config import BUNDLE_SOL, BUNDLE_DELAY
                amount = BUNDLE_SOL
                delay = BUNDLE_DELAY
            else:
                delay = 2.0
            
            sol_lamports = int(amount * 1e9)
            num_wallets = min(len(self.wallets), NUM_WALLETS)
            
            print(f"[TARGET] OPTIMIZED sequential bundling")
            print(f"   Wallets: {num_wallets} (reduced for efficiency)")
            print(f"   Per wallet: {amount} SOL ({sol_lamports} lamports)")
            print(f"   Delay: {delay}s ±1s random (organic)")
            print(f"   Total cost: {amount * num_wallets:.4f} SOL (~${amount * num_wallets * 194:.2f})")
            
            success_count = 0
            failure_count = 0
            
            # Sequential buys with delay (appears organic, not atomic bot)
            for i, wallet in enumerate(self.wallets[:num_wallets]):
                try:
                    print(f"   [{i+1}/{num_wallets}] Buying via Pump.fun...")
                    
                    # Try Pump.fun buy
                    result = await self.pumpfun.buy_tokens(
                        buyer_wallet=wallet,
                        mint_address=mint,
                        sol_amount=amount,
                        slippage_bps=1200  # 12% slippage (optimized from 15%)
                    )
                    
                    if result and result.get("signature"):
                        success_count += 1
                        failure_count = 0  # Reset on success
                        print(f"   [{i+1}] [OK] TX: {result['signature'][:16]}...")
                    else:
                        # Fallback to Jupiter
                        print(f"   [{i+1}] Trying Jupiter fallback...")
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            jupiter_result = await asyncio.get_event_loop().run_in_executor(
                                executor,
                                buy_token_simple,
                                wallet,
                                mint,
                                sol_lamports,
                                self.rpc_url,
                                1200
                            )
                            if jupiter_result:
                                success_count += 1
                                failure_count = 0
                                print(f"   [{i+1}] [OK] Jupiter: {jupiter_result[:16]}...")
                            else:
                                failure_count += 1
                
                except Exception as e:
                    print(f"   [{i+1}] [ERROR] {e}")
                    failure_count += 1
                
                # Auto-abort if first 3 buys fail (save costs)
                if i < 3 and failure_count >= 3:
                    print(f"\n[ABORT] First 3 buys failed - aborting to save costs")
                    print(f"[INFO] Partial execution: {success_count}/{i+1}")
                    break
                
                # CRITICAL: Delay for organic appearance (2-4s random)
                import random
                actual_delay = delay + random.uniform(-1.0, 1.0)
                await asyncio.sleep(actual_delay)
            
            coverage = (success_count / num_wallets) * 100
            print(f"[OK] Bundle complete: {success_count}/{num_wallets} ({coverage:.1f}%)")
            print(f"[INFO] Total volume: {amount * success_count:.4f} SOL")
            
            return success_count > 0
            
        except Exception as e:
            print(f"[ERROR] Bundle buy failed: {e}")
            return False

    async def create_and_bundle(self, name, symbol, image_url, description="Meme token on Pump.fun"):
        """Create token with atomic bundled buys (via Jito)."""
        try:
            # Create fresh AsyncClient for this call (avoid event loop issues)
            self.client = AsyncClient(self.rpc_url)
            
            # create_token now does bundled creation + initial buys atomically via Jito
            # No need to call bundle_buy separately!
            mint = await self.create_token(name, symbol, image_url, description)
            if not mint:
                return None
            
            print(f"[OK] Launched {name} with atomic bundled buys via Jito!")
            return mint
            
        except Exception as e:
            print(f"[ERROR] Create and bundle failed: {e}")
            return None
