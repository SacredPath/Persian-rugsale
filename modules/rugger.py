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
from config import NUM_WALLETS, BUNDLE_SOL

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
        REAL rug execution with ATOMIC Jito bundling
        
        Args:
            mint: Token mint address
            partial: If True, sell only 50% (early salvage mode)
        
        Critical: Uses Jito bundles for atomic execution (MEV protection)
        - Bonding curve tokens: Use PumpPortal bundled sells
        - Graduated tokens: Use Jupiter (sequential, can't bundle across protocols)
        """
        try:
            # Create fresh AsyncClient for this call (avoid event loop issues)
            self.client = AsyncClient(self.rpc_url)
            
            rug_mode = "PARTIAL (50%)" if partial else "FULL (100%)"
            print(f"[RUG] EXECUTING: {mint[:8]}... Mode: {rug_mode}")
            print(f"[INFO] Checking graduation status...")
            
            # Check if token graduated (moved to PumpSwap/Raydium)
            token_data = await self.pumpfun.get_token_data(mint)
            graduated = token_data and token_data.get('graduated', False) if token_data else False
            
            if graduated:
                print(f"[WARNING] Token GRADUATED - using Jupiter (sequential, not bundled)")
                return await self._execute_graduated(mint, partial)
            else:
                # ALWAYS use Jito bundles for rugs (atomic execution critical for MEV protection)
                print(f"[INFO] Token on bonding curve - using JITO ATOMIC BUNDLE")
                print(f"[INFO] Rugs ALWAYS use Jito (atomicity > cost)")
                return await self._execute_bundled_pumpfun(mint, partial)
                
        except Exception as e:
            print(f"[ERROR] Rug failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _execute_bundled_pumpfun(self, mint, partial=False):
        """
        Execute rug via Jito atomic bundle (for Pump.fun bonding curve tokens)
        
        This is the PRIMARY method - uses same pattern as create_token_bundled
        """
        try:
            import httpx
            import base58
            import random
            from config import JITO_TIP_RUG
            
            # Import transaction utilities
            try:
                from solders.system_program import TransferParams, transfer as system_transfer
                from solders.message import Message
                from solders.transaction import VersionedTransaction as SoldersVersionedTransaction
                from solders.pubkey import Pubkey
                from solders.signature import Signature
                USE_SOLDERS = True
            except ImportError:
                from solana.system_program import TransferParams, transfer as system_transfer
                from solana.transaction import Transaction as LegacyTransaction
                from solana.publickey import PublicKey as Pubkey
                USE_SOLDERS = False
            
            # STEP 1: Collect wallets with tokens
            print(f"[STEP 1] Checking wallet balances...")
            sell_transactions = []
            
            for i, wallet in enumerate(self.wallets[:20]):
                try:
                    wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                    balance = get_token_balance_simple(wallet_addr, mint, self.rpc_url)
                    
                    if balance > 0:
                        sell_amount = int(balance * 0.5) if partial else balance
                        sell_transactions.append({
                            'wallet': wallet,
                            'wallet_addr': wallet_addr,
                            'balance': sell_amount
                        })
                        mode_tag = " (50%)" if partial else ""
                        print(f"   [OK] {wallet_addr[:8]}: {sell_amount:,.0f} tokens{mode_tag}")
                except Exception as e:
                    print(f"   [ERROR] Wallet {i}: {e}")
            
            if not sell_transactions:
                print(f"[ERROR] No tokens found in any wallet")
                return False
            
            print(f"[OK] Found {len(sell_transactions)} wallets with tokens")
            
            # STEP 2: Build bundled sell transaction arguments
            print(f"[STEP 2] Building bundled sell transactions...")
            
            from modules.pumpfun_real import PUMPPORTAL_TRADE_LOCAL
            
            bundled_tx_args = []
            for tx_data in sell_transactions:
                bundled_tx_args.append({
                    'publicKey': tx_data['wallet_addr'],
                    'action': 'sell',
                    'mint': mint,
                    'denominatedInSol': 'false',  # Sell by token amount
                    'amount': tx_data['balance'],  # Token amount to sell
                    'slippage': 15,  # 15% slippage for fast execution
                    'priorityFee': 0.0001,
                    'pool': 'pump'
                })
            
            print(f"[INFO] Bundle: {len(bundled_tx_args)} sell transactions")
            
            # STEP 3: Generate unsigned transactions from PumpPortal
            print(f"[STEP 3] Generating unsigned transactions...")
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    PUMPPORTAL_TRADE_LOCAL,
                    json=bundled_tx_args,
                    headers={'Content-Type': 'application/json'}
                )
                
                print(f"[API] Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"[ERROR] PumpPortal error: {response.text}")
                    return False
                
                unsigned_transactions = response.json()
                print(f"[OK] Generated {len(unsigned_transactions)} unsigned transactions")
            
            # STEP 4: Sign transactions locally
            print(f"[STEP 4] Signing transactions...")
            
            encoded_signed_transactions = []
            tx_signatures = []
            
            for i, encoded_tx in enumerate(unsigned_transactions):
                try:
                    # Decode unsigned transaction
                    tx_bytes = base58.b58decode(encoded_tx)
                    
                    # Import VersionedTransaction
                    if USE_SOLDERS:
                        from solders.transaction import VersionedTransaction
                    else:
                        from solana.transaction import VersionedTransaction
                    
                    unsigned_tx = VersionedTransaction.from_bytes(tx_bytes)
                    
                    # Sign with seller wallet
                    seller_wallet = sell_transactions[i]['wallet']
                    signed_tx = VersionedTransaction(unsigned_tx.message, [seller_wallet])
                    
                    # Encode signed transaction
                    signed_tx_bytes = bytes(signed_tx)
                    encoded_signed_tx = base58.b58encode(signed_tx_bytes).decode()
                    encoded_signed_transactions.append(encoded_signed_tx)
                    
                    # Store signature for verification
                    tx_sig = str(signed_tx.signatures[0])
                    tx_signatures.append(tx_sig)
                    
                    print(f"[OK] Signed TX {i}: {tx_sig[:16]}...")
                    
                except Exception as sign_error:
                    print(f"[ERROR] Failed to sign TX {i}: {sign_error}")
                    return False
            
            # STEP 5: Create Jito tip transaction
            print(f"[STEP 5] Creating Jito tip transaction...")
            
            from modules.pumpfun_real import JITO_TIP_ACCOUNTS
            
            # Use higher tip for rugs (critical for profit)
            jito_tip_lamports = int(JITO_TIP_RUG * 1e9)
            print(f"[INFO] Jito tip: {JITO_TIP_RUG} SOL (~${JITO_TIP_RUG * 194:.2f}) - HIGHER for rug priority")
            
            # Pick random Jito tip account
            tip_account = random.choice(JITO_TIP_ACCOUNTS)
            tip_pubkey = Pubkey.from_string(tip_account)
            
            # First wallet pays the tip (has most SOL)
            tipper_wallet = sell_transactions[0]['wallet']
            tipper_pubkey = Pubkey.from_string(sell_transactions[0]['wallet_addr'])
            
            # Get recent blockhash
            blockhash_response = await self.client.get_latest_blockhash()
            recent_blockhash = blockhash_response.value.blockhash
            
            # Create tip instruction
            tip_instruction = system_transfer(
                TransferParams(
                    from_pubkey=tipper_pubkey,
                    to_pubkey=tip_pubkey,
                    lamports=jito_tip_lamports
                )
            )
            
            # Build tip transaction
            if USE_SOLDERS:
                tip_message = Message.new_with_blockhash(
                    [tip_instruction],
                    tipper_pubkey,
                    recent_blockhash
                )
                tip_tx = SoldersVersionedTransaction(tip_message, [tipper_wallet])
            else:
                tip_tx = LegacyTransaction()
                tip_tx.recent_blockhash = recent_blockhash
                tip_tx.add(tip_instruction)
                tip_tx.sign(tipper_wallet)
            
            # Encode tip transaction
            tip_tx_bytes = bytes(tip_tx)
            tip_tx_encoded = base58.b58encode(tip_tx_bytes).decode()
            
            # Add tip transaction to bundle (must be last)
            bundle_with_tip = encoded_signed_transactions + [tip_tx_encoded]
            
            print(f"[OK] Bundle prepared: {len(encoded_signed_transactions)} sells + 1 tip = {len(bundle_with_tip)} total")
            
            # STEP 6: Submit bundle to Jito with retry
            print(f"[STEP 6] Submitting bundle to Jito...")
            
            from modules.pumpfun_real import JITO_BLOCK_ENGINES
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # CRITICAL: Wait for Jito leader slot (prevents 429 spam)
                    leader_ready = await self.pumpfun._wait_for_jito_leader(max_wait_seconds=10)
                    if not leader_ready and attempt < max_attempts - 1:
                        print(f"[WARNING] Jito not ready - will retry with backoff")
                        # Exponential backoff: 3s, 6s, 12s...
                        backoff = 10 * (2 ** attempt)
                        await asyncio.sleep(backoff)
                        continue
                    
                    # Try different Jito block engines
                    jito_url = random.choice(JITO_BLOCK_ENGINES)
                    bundle_endpoint = f"{jito_url}/api/v1/bundles"
                    
                    print(f"[ATTEMPT {attempt + 1}/{max_attempts}] Using {jito_url.split('//')[1].split('.')[0]} region...")
                    
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        jito_response = await http_client.post(
                            bundle_endpoint,
                            headers={'Content-Type': 'application/json'},
                            json={
                                'jsonrpc': '2.0',
                                'id': 1,
                                'method': 'sendBundle',
                                'params': [bundle_with_tip]
                            }
                        )
                        
                        print(f"[API] Response status: {jito_response.status_code}")
                        
                        if jito_response.status_code == 200:
                            jito_result = jito_response.json()
                            
                            # Check for error in response
                            if 'error' in jito_result:
                                error_msg = jito_result['error'].get('message', str(jito_result['error']))
                                print(f"[ERROR] Jito error: {error_msg}")
                                if attempt < max_attempts - 1:
                                    # Exponential backoff
                                    backoff = 10 * (2 ** attempt)
                                    print(f"[RETRY] Waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    return False
                            
                            bundle_id = jito_result.get('result')
                            
                            # CRITICAL: Check if bundle_id is valid
                            if not bundle_id:
                                print(f"[ERROR] No bundle ID returned from Jito")
                                print(f"[ERROR] Jito response: {jito_result}")
                                if attempt < max_attempts - 1:
                                    backoff = 10 * (2 ** attempt)
                                    print(f"[RETRY] Waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    return False
                            
                            print(f"[OK] RUG BUNDLE SUBMITTED!")
                            print(f"[INFO] Bundle ID: {bundle_id}")
                            print(f"[INFO] Tip: {JITO_TIP_RUG} SOL to {tip_account[:8]}...")
                            
                            # Print transaction links
                            for i, signature in enumerate(tx_signatures):
                                wallet_addr = sell_transactions[i]['wallet_addr']
                                print(f"[TX {i}] {wallet_addr[:8]}: https://solscan.io/tx/{signature}")
                            
                            # PROPER JITO POLLER: Check bundle status via Jito API (not Solana RPC)
                            bundle_result = await self.pumpfun._check_bundle_status(
                                bundle_id=bundle_id,
                                jito_url=jito_url,
                                max_wait_seconds=60  # Poll for up to 60 seconds
                            )
                            
                            if bundle_result['landed']:
                                print(f"[OK] RUG BUNDLE LANDED!")
                                print(f"[OK] {len(sell_transactions)} sells executed atomically")
                                print(f"[OK] Final status: {bundle_result['status']}")
                                
                                # Calculate profits (estimate)
                                total_tokens_sold = sum(tx['balance'] for tx in sell_transactions)
                                print(f"[PROFIT] Sold {total_tokens_sold:,.0f} tokens")
                                print(f"[INFO] Check wallet balances for exact SOL recovered")
                                
                                return True
                            else:
                                status = bundle_result['status']
                                print(f"[ERROR] Rug bundle did not land: {status}")
                                
                                # Log detailed failure info if available
                                if bundle_result.get('details'):
                                    print(f"[DEBUG] Bundle details: {bundle_result['details']}")
                                
                                # Check Solscan manually
                                print(f"[INFO] Verify on Solscan: https://solscan.io/tx/{tx_signatures[0]}")
                                print(f"[INFO] Check Jito Explorer: https://explorer.jito.wtf/bundle/{bundle_id}")
                                
                                # Decide whether to retry
                                if status == 'failed':
                                    print(f"[ERROR] Bundle FAILED - will not retry this bundle")
                                    if attempt >= max_attempts - 1:
                                        print(f"[ERROR] All Jito attempts exhausted - rug FAILED")
                                        return False
                                    else:
                                        print(f"[RETRY] Creating new bundle with fresh blockhash...")
                                        backoff = 10 * (2 ** attempt)
                                        await asyncio.sleep(backoff)
                                        continue
                                elif status == 'timeout':
                                    print(f"[WARNING] Bundle timeout - may still land later")
                                    if attempt >= max_attempts - 1:
                                        print(f"[WARNING] Rug execution uncertain - check links above")
                                        return False
                                    else:
                                        print(f"[RETRY] Trying new bundle...")
                                        backoff = 10 * (2 ** attempt)
                                        await asyncio.sleep(backoff)
                                        continue
                                else:
                                    # Unknown error
                                    if attempt >= max_attempts - 1:
                                        print(f"[ERROR] All Jito attempts exhausted")
                                        return False
                                    else:
                                        backoff = 10 * (2 ** attempt)
                                        print(f"[RETRY] Trying again in {backoff}s...")
                                        await asyncio.sleep(backoff)
                                        continue
                        else:
                            print(f"[ERROR] Jito HTTP error: {jito_response.status_code}")
                            print(f"[ERROR] Response: {jito_response.text}")
                            
                            # Handle 429 rate limit specially
                            if jito_response.status_code == 429:
                                if attempt < max_attempts - 1:
                                    # Longer backoff for rate limits
                                    backoff = 5 * (2 ** attempt)  # 5s, 10s, 20s
                                    print(f"[429] Rate limited - waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    print(f"[ERROR] Rate limit persists - rug execution failed")
                                    return False
                            else:
                                if attempt < max_attempts - 1:
                                    backoff = 10 * (2 ** attempt)
                                    print(f"[RETRY] Waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    return False
                
                except Exception as jito_err:
                    print(f"[ERROR] Jito submission error: {jito_err}")
                    if attempt < max_attempts - 1:
                        backoff = 10 * (2 ** attempt)
                        print(f"[RETRY] Waiting {backoff}s before retry...")
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        print(f"[ERROR] All Jito attempts failed")
                        return False
            
                return False
                
        except Exception as e:
            print(f"[ERROR] Bundled rug failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _execute_graduated(self, mint, partial=False):
        """
        Fallback for graduated tokens (uses Jupiter, sequential)
        
        Note: Can't bundle Jupiter swaps with Jito (different protocols)
        This will be slower and subject to slippage, but necessary for graduated tokens
        """
        try:
            print(f"[FALLBACK] Graduated token - sequential Jupiter sells")
            
            success_count = 0
            total_sol_received = 0.0
            
            for i, wallet in enumerate(self.wallets[:20]):
                try:
                    wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                    balance = get_token_balance_simple(wallet_addr, mint, self.rpc_url)
                    
                    if balance > 0:
                        sell_amount = int(balance * 0.5) if partial else balance
                        
                        # Use Jupiter for graduated tokens
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            result = await asyncio.get_event_loop().run_in_executor(
                                executor,
                                sell_token_simple,
                                wallet,
                                mint,
                                sell_amount,
                                self.rpc_url,
                                1500  # 15% slippage
                            )
                            
                            if result:
                    success_count += 1
                                print(f"   [{success_count}] [OK] {wallet_addr[:8]}")
                                
                                # Small delay between sells
                                await asyncio.sleep(1.0)
                
                except Exception as e:
                    print(f"   [ERROR] Wallet {i}: {e}")
            
            print(f"[OK] Graduated rug complete: {success_count} sells")
            return success_count > 0
            
        except Exception as e:
            print(f"[ERROR] Graduated rug failed: {e}")
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
