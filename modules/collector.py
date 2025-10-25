"""
Profit Collector - Consolidates SOL from bot wallets to main wallet
"""
import asyncio
from solana.rpc.async_api import AsyncClient
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
except ImportError:
    from solana.keypair import Keypair
    from solana.publickey import PublicKey as Pubkey

from .utils import load_wallets
from .retry_utils import retry_async
from config import MAIN_WALLET, NUM_WALLETS

class ProfitCollector:
    """Collects profits from all bot wallets to main wallet"""
    
    def __init__(self, rpc_url):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        self.wallets = load_wallets()
        
        if not MAIN_WALLET:
            print("[WARNING] ProfitCollector disabled - MAIN_WALLET not set")
            self.enabled = False
        else:
            self.enabled = True
            print(f"[OK] Profit Collector initialized: {len(self.wallets)} wallets -> {MAIN_WALLET[:8]}...")
    
    @retry_async(max_attempts=3, delay=1.0)
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
            print(f"[COLLECT] Starting profit collection...")
            print(f"[INFO] Target: {MAIN_WALLET}")
            
            results = {
                "success": True,
                "collected": 0.0,
                "transferred": 0,
                "failed": 0,
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
            
            # Collect from each wallet
            for i, wallet in enumerate(self.wallets[:NUM_WALLETS]):
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
                    
                    print(f"   [{i}] {wallet_addr[:8]}... Balance: {balance_sol:.6f} SOL")
                    
                    # Skip if balance too low (need to keep some for rent + fees)
                    MIN_BALANCE = 0.001  # Keep 0.001 SOL for rent
                    if balance_sol <= MIN_BALANCE:
                        print(f"   [{i}] Skipping (balance too low)")
                        results["details"].append({
                            "wallet": i,
                            "address": wallet_addr,
                            "status": "skipped",
                            "balance": balance_sol,
                            "reason": "Balance too low"
                        })
                        continue
                    
                    # Calculate transfer amount (leave minimum for rent)
                    transfer_lamports = balance_lamports - 5000  # Leave 0.000005 SOL for rent
                    transfer_sol = transfer_lamports / 1e9
                    
                    if transfer_lamports <= 0:
                        print(f"   [{i}] Skipping (insufficient after fees)")
                        results["details"].append({
                            "wallet": i,
                            "address": wallet_addr,
                            "status": "skipped",
                            "balance": balance_sol,
                            "reason": "Insufficient after fees"
                        })
                        continue
                    
                    # Build transfer transaction
                    print(f"   [{i}] Transferring {transfer_sol:.6f} SOL...")
                    
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
                    
                    # Build and sign transaction
                    tx = Transaction([transfer_ix], wallet_pubkey, recent_blockhash)
                    tx.sign([wallet])
                    
                    # Send transaction
                    send_result = await self.client.send_raw_transaction(
                        bytes(tx),
                        opts={"skipPreflight": False, "preflightCommitment": "confirmed"}
                    )
                    
                    if send_result.value:
                        signature = str(send_result.value)
                        print(f"   [{i}] [OK] TX: {signature[:16]}...")
                        
                        results["transferred"] += 1
                        results["collected"] += transfer_sol
                        results["details"].append({
                            "wallet": i,
                            "address": wallet_addr,
                            "status": "success",
                            "amount": transfer_sol,
                            "signature": signature
                        })
                    else:
                        print(f"   [{i}] [ERROR] Transaction failed")
                        results["failed"] += 1
                        results["details"].append({
                            "wallet": i,
                            "address": wallet_addr,
                            "status": "failed",
                            "reason": "Transaction rejected"
                        })
                    
                except Exception as e:
                    print(f"   [{i}] [ERROR] {e}")
                    results["failed"] += 1
                    results["details"].append({
                        "wallet": i,
                        "status": "error",
                        "reason": str(e)
                    })
            
            # Summary
            print(f"\n[COLLECT] Complete:")
            print(f"   Transferred: {results['transferred']}/{NUM_WALLETS}")
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

