"""
Profit Collector - Consolidates SOL from bot wallets to main wallet
"""
import asyncio
from solana.rpc.async_api import AsyncClient

# Import system program and transaction with fallback
try:
    from solders.system_program import TransferParams, transfer
    from solders.message import Message
    from solders.transaction import VersionedTransaction as SoldersVersionedTransaction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    USE_SOLDERS = True
except ImportError:
    # Fallback for older solana-py versions
    from solana.system_program import TransferParams, transfer
    from solana.transaction import Transaction as LegacyTransaction
    from solana.keypair import Keypair
    from solana.publickey import PublicKey as Pubkey
    USE_SOLDERS = False

from .utils import load_wallets
from .retry_utils import retry_async
from config import MAIN_WALLET, NUM_WALLETS

class ProfitCollector:
    """Collects profits from all bot wallets to main wallet"""
    
    def __init__(self, rpc_url):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        self.wallets = load_wallets()
        
        # Validate MAIN_WALLET
        if not MAIN_WALLET:
            print("[WARNING] ProfitCollector disabled - MAIN_WALLET not set")
            self.enabled = False
        elif len(MAIN_WALLET) != 44 and len(MAIN_WALLET) != 43:
            print(f"[ERROR] Invalid MAIN_WALLET length: {len(MAIN_WALLET)} (expected 43-44 chars)")
            self.enabled = False
        else:
            # Test if it's a valid pubkey format
            try:
                test_pubkey = Pubkey.from_string(MAIN_WALLET)
                self.enabled = True
                print(f"[OK] Profit Collector initialized: {len(self.wallets)} wallets -> {MAIN_WALLET[:8]}...")
            except Exception as e:
                print(f"[ERROR] Invalid MAIN_WALLET format: {e}")
                self.enabled = False
    
    async def get_collection_preview(self):
        """
        Preview how much SOL will be collected (without actually transferring).
        
        Returns:
            dict: Preview with total collectible, per-wallet details, and MAIN_WALLET address
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "MAIN_WALLET not configured",
                "collectible": 0,
                "details": []
            }
        
        try:
            # Create fresh AsyncClient
            self.client = AsyncClient(self.rpc_url)
            
            preview = {
                "success": True,
                "collectible": 0.0,
                "wallets_with_funds": 0,
                "main_wallet": MAIN_WALLET,
                "details": []
            }
            
            # SAFETY CHECK: Ensure MAIN_WALLET is not one of the bot wallets
            try:
                main_pubkey = Pubkey.from_string(MAIN_WALLET)
                main_wallet_str = str(main_pubkey)
                
                for i, wallet in enumerate(self.wallets[:NUM_WALLETS]):
                    try:
                        bot_wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                        if bot_wallet_addr == main_wallet_str:
                            print(f"[ERROR] MAIN_WALLET is bot wallet {i} - cannot collect")
                            return {
                                "success": False,
                                "error": f"MAIN_WALLET is bot wallet {i} (cannot transfer to self)",
                                "collectible": 0,
                                "details": []
                            }
                    except Exception as e:
                        print(f"[WARNING] Could not verify wallet {i}: {e}")
            except Exception as e:
                print(f"[ERROR] Invalid MAIN_WALLET: {e}")
                return {
                    "success": False,
                    "error": f"Invalid MAIN_WALLET: {e}",
                    "collectible": 0,
                    "details": []
                }
            
            RENT_EXEMPT = 890880  # Solana standard rent-exempt minimum
            TX_FEE_ESTIMATE = 5000  # ~0.000005 SOL transaction fee
            RESERVE = RENT_EXEMPT + TX_FEE_ESTIMATE
            MIN_BALANCE_LAMPORTS = 900000  # 0.0009 SOL minimum
            
            wallets_to_check = self.wallets[:NUM_WALLETS]
            
            for i, wallet in enumerate(wallets_to_check):
                try:
                    # Get wallet address
                    try:
                        wallet_addr = str(wallet.pubkey())
                    except:
                        wallet_addr = str(wallet.public_key)
                    
                    wallet_pubkey = Pubkey.from_string(wallet_addr)
                    
                    # Get balance
                    balance_resp = await self.client.get_balance(wallet_pubkey)
                    balance_lamports = balance_resp.value if balance_resp.value else 0
                    balance_sol = balance_lamports / 1e9
                    
                    # Calculate collectible amount
                    if balance_lamports > MIN_BALANCE_LAMPORTS:
                        collectible_lamports = balance_lamports - RESERVE
                        collectible_sol = collectible_lamports / 1e9
                        
                        if collectible_sol > 0:
                            preview["collectible"] += collectible_sol
                            preview["wallets_with_funds"] += 1
                            preview["details"].append({
                                "wallet": i,
                                "address": wallet_addr,
                                "balance": balance_sol,
                                "collectible": collectible_sol
                            })
                        else:
                            preview["details"].append({
                                "wallet": i,
                                "address": wallet_addr,
                                "balance": balance_sol,
                                "collectible": 0,
                                "reason": "Insufficient after fees"
                            })
                    else:
                        preview["details"].append({
                            "wallet": i,
                            "address": wallet_addr,
                            "balance": balance_sol,
                            "collectible": 0,
                            "reason": "Balance too low"
                        })
                
                except Exception as e:
                    print(f"[WARNING] Could not check wallet {i}: {e}")
                    preview["details"].append({
                        "wallet": i,
                        "error": str(e)
                    })
            
            return preview
            
        except Exception as e:
            print(f"[ERROR] Preview failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "collectible": 0,
                "details": []
            }
    
    @retry_async(max_attempts=2, delay=0.5)
    async def _transfer_single(self, wallet, wallet_index, main_pubkey):
        """
        Transfer SOL from a single wallet to main wallet (with retry).
        
        Args:
            wallet: Keypair object
            wallet_index: Wallet number (for logging)
            main_pubkey: Main wallet Pubkey object
        
        Returns:
            dict: Transfer result with status, amount, signature
        """
        try:
            # Get wallet address
            try:
                wallet_addr = str(wallet.pubkey())
            except:
                wallet_addr = str(wallet.public_key)
            
            wallet_pubkey = Pubkey.from_string(wallet_addr)
            
            # Get balance
            balance_resp = await self.client.get_balance(wallet_pubkey)
            balance_lamports = balance_resp.value if balance_resp.value else 0
            balance_sol = balance_lamports / 1e9
            
            print(f"   [{wallet_index}] {wallet_addr[:8]}... Balance: {balance_sol:.6f} SOL")
            
            # Skip if balance too low
            MIN_BALANCE_LAMPORTS = 900000  # 0.0009 SOL minimum
            if balance_lamports <= MIN_BALANCE_LAMPORTS:
                print(f"   [{wallet_index}] Skipping (balance < 0.0009 SOL)")
                return {
                    "wallet": wallet_index,
                    "address": wallet_addr,
                    "status": "skipped",
                    "balance": balance_sol,
                    "reason": "Balance too low (< 0.0009 SOL)"
                }
            
            # Calculate transfer amount
            RENT_EXEMPT = 890880  # Solana standard rent-exempt minimum
            TX_FEE_ESTIMATE = 5000  # ~0.000005 SOL transaction fee
            RESERVE = RENT_EXEMPT + TX_FEE_ESTIMATE
            
            transfer_lamports = balance_lamports - RESERVE
            transfer_sol = transfer_lamports / 1e9
            
            if transfer_lamports <= 0:
                print(f"   [{wallet_index}] Skipping (insufficient after fees)")
                return {
                    "wallet": wallet_index,
                    "address": wallet_addr,
                    "status": "skipped",
                    "balance": balance_sol,
                    "reason": "Insufficient after fees"
                }
            
            # Build transfer transaction
            print(f"   [{wallet_index}] Transferring {transfer_sol:.6f} SOL...")
            
            # Get recent blockhash
            blockhash_resp = await self.client.get_latest_blockhash()
            recent_blockhash = blockhash_resp.value.blockhash
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=wallet_pubkey,
                    to_pubkey=main_pubkey,
                    lamports=transfer_lamports
                )
            )
            
            # Build and sign transaction (different for solders vs legacy)
            if USE_SOLDERS:
                # Solders: Use Message and VersionedTransaction
                message = Message.new_with_blockhash(
                    [transfer_ix],
                    wallet_pubkey,
                    recent_blockhash
                )
                tx = SoldersVersionedTransaction(message, [wallet])
            else:
                # Legacy: Use Transaction with add() and sign()
                tx = LegacyTransaction()
                tx.recent_blockhash = recent_blockhash
                tx.add(transfer_ix)
                tx.sign(wallet)
            
            # Send transaction
            send_result = await self.client.send_raw_transaction(
                bytes(tx),
                opts={"skipPreflight": False, "preflightCommitment": "confirmed"}
            )
            
            if send_result.value:
                signature = str(send_result.value)
                print(f"   [{wallet_index}] [OK] TX: {signature[:16]}...")
                
                return {
                    "wallet": wallet_index,
                    "address": wallet_addr,
                    "status": "success",
                    "amount": transfer_sol,
                    "signature": signature
                }
            else:
                print(f"   [{wallet_index}] [ERROR] Transaction failed")
                return {
                    "wallet": wallet_index,
                    "address": wallet_addr,
                    "status": "failed",
                    "reason": "Transaction rejected"
                }
        
        except Exception as e:
            print(f"   [{wallet_index}] [ERROR] {e}")
            # Try to get wallet address for error reporting
            try:
                wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
            except:
                wallet_addr = "unknown"
            
            return {
                "wallet": wallet_index,
                "address": wallet_addr,
                "status": "error",
                "reason": str(e)
            }
    
    async def collect_all(self):
        """
        Collect all SOL from bot wallets to main wallet.
        
        Returns:
            dict: Results with success count and total collected
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "MAIN_WALLET not configured",
                "collected": 0,
                "details": []
            }
        
        try:
            # Create fresh AsyncClient for this call (avoid event loop issues)
            self.client = AsyncClient(self.rpc_url)
            
            print(f"[COLLECT] Starting profit collection...")
            print(f"[INFO] Target: {MAIN_WALLET}")
            
            results = {
                "success": True,
                "collected": 0.0,
                "transferred": 0,
                "failed": 0,
                "total_wallets": 0,  # Will be set after processing
                "details": []
            }
            
            # Get main wallet pubkey
            try:
                main_pubkey = Pubkey.from_string(MAIN_WALLET)
            except Exception as e:
                print(f"[ERROR] Invalid MAIN_WALLET address: {e}")
                return {
                    "success": False,
                    "error": f"Invalid MAIN_WALLET: {e}",
                    "collected": 0,
                    "details": []
                }
            
            # SAFETY CHECK: Ensure MAIN_WALLET is not one of the bot wallets
            main_wallet_str = str(main_pubkey)
            for i, wallet in enumerate(self.wallets[:NUM_WALLETS]):
                try:
                    bot_wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                    if bot_wallet_addr == main_wallet_str:
                        print(f"[ERROR] MAIN_WALLET is bot wallet {i} - cannot transfer to self!")
                        return {
                            "success": False,
                            "error": f"MAIN_WALLET is bot wallet {i} (cannot transfer to self)",
                            "collected": 0,
                            "details": []
                        }
                except Exception as e:
                    print(f"[WARNING] Could not verify wallet {i}: {e}")
            
            # Collect from each wallet (with per-wallet retry)
            wallets_to_process = self.wallets[:NUM_WALLETS]
            num_wallets_processed = len(wallets_to_process)
            results["total_wallets"] = num_wallets_processed
            
            for i, wallet in enumerate(wallets_to_process):
                result = await self._transfer_single(wallet, i, main_pubkey)
                
                results["details"].append(result)
                
                if result["status"] == "success":
                    results["transferred"] += 1
                    results["collected"] += result["amount"]
                elif result["status"] in ["failed", "error"]:
                    results["failed"] += 1
            
            # Summary
            print(f"\n[COLLECT] Complete:")
            print(f"   Transferred: {results['transferred']}/{num_wallets_processed}")
            print(f"   Failed: {results['failed']}")
            print(f"   Total collected: {results['collected']:.6f} SOL")
            
            results["success"] = results["transferred"] > 0
            return results
            
        except Exception as e:
            print(f"[ERROR] Collection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "collected": 0,
                "details": []
            }

