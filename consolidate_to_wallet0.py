"""
Consolidate SOL from bot wallets into wallet_0
"""
import asyncio
from solana.rpc.async_api import AsyncClient
from config import RPC_URL
from modules.utils import load_wallets

# Import system program and transaction with fallback
try:
    from solders.system_program import TransferParams, transfer
    from solders.message import Message
    from solders.transaction import VersionedTransaction
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    USE_SOLDERS = True
except ImportError:
    from solana.system_program import TransferParams, transfer
    from solana.transaction import Transaction
    from solana.keypair import Keypair
    from solana.publickey import PublicKey as Pubkey
    USE_SOLDERS = False

async def consolidate_to_wallet0():
    """
    Transfer all SOL from bot wallets 1-3 to wallet_0.
    """
    try:
        print(f"\n{'='*60}")
        print("CONSOLIDATE BOT WALLETS TO WALLET_0")
        print(f"{'='*60}\n")
        
        # Load all bot wallets
        wallets = load_wallets()
        if not wallets or len(wallets) < 2:
            print("[ERROR] Not enough wallets found! Need at least 2 wallets.")
            return False
        
        wallet_0 = wallets[0]
        wallet_0_addr = str(wallet_0.pubkey() if hasattr(wallet_0, 'pubkey') else wallet_0.public_key)
        to_pubkey = Pubkey.from_string(wallet_0_addr)
        
        print(f"[INFO] Destination: wallet_0")
        print(f"[INFO] Address: {wallet_0_addr}\n")
        
        # Connect to RPC
        client = AsyncClient(RPC_URL)
        
        # Check wallet_0 initial balance
        balance_resp = await client.get_balance(to_pubkey)
        initial_balance = balance_resp.value / 1e9 if balance_resp.value else 0.0
        print(f"[INFO] wallet_0 current balance: {initial_balance:.6f} SOL\n")
        
        # Process each wallet
        total_transferred = 0.0
        successful_transfers = 0
        
        for i in range(1, len(wallets)):
            wallet = wallets[i]
            wallet_addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
            from_pubkey = Pubkey.from_string(wallet_addr)
            
            print(f"[{i}] Checking wallet_{i}...")
            print(f"    Address: {wallet_addr}")
            
            # Get balance
            balance_resp = await client.get_balance(from_pubkey)
            balance_lamports = balance_resp.value if balance_resp.value else 0
            balance_sol = balance_lamports / 1e9
            print(f"    Balance: {balance_sol:.6f} SOL")
            
            # Skip if balance too low
            MIN_BALANCE = 900000  # 0.0009 SOL (rent-exempt + fees)
            if balance_lamports <= MIN_BALANCE:
                print(f"    [SKIP] Balance too low (< 0.0009 SOL)\n")
                continue
            
            # Calculate transfer amount (leave some for rent + fees)
            RESERVE = 895880  # Rent-exempt (890880) + TX fee (5000)
            transfer_lamports = balance_lamports - RESERVE
            transfer_sol = transfer_lamports / 1e9
            
            if transfer_lamports <= 0:
                print(f"    [SKIP] Insufficient after fees\n")
                continue
            
            print(f"    [TRANSFER] Sending {transfer_sol:.6f} SOL to wallet_0...")
            
            try:
                # Get recent blockhash
                blockhash_resp = await client.get_latest_blockhash()
                recent_blockhash = blockhash_resp.value.blockhash
                
                # Create transfer instruction
                transfer_ix = transfer(
                    TransferParams(
                        from_pubkey=from_pubkey,
                        to_pubkey=to_pubkey,
                        lamports=transfer_lamports
                    )
                )
                
                # Build and sign transaction
                if USE_SOLDERS:
                    message = Message.new_with_blockhash(
                        [transfer_ix],
                        from_pubkey,
                        recent_blockhash
                    )
                    tx = VersionedTransaction(message, [wallet])
                else:
                    tx = Transaction()
                    tx.recent_blockhash = recent_blockhash
                    tx.add(transfer_ix)
                    tx.sign(wallet)
                
                # Send transaction
                send_result = await client.send_raw_transaction(
                    bytes(tx),
                    opts={"skipPreflight": False, "preflightCommitment": "confirmed"}
                )
                
                if send_result.value:
                    signature = str(send_result.value)
                    print(f"    [OK] Transfer successful!")
                    print(f"    TX: https://solscan.io/tx/{signature}")
                    total_transferred += transfer_sol
                    successful_transfers += 1
                else:
                    print(f"    [ERROR] Transaction rejected")
                
            except Exception as e:
                print(f"    [ERROR] Transfer failed: {e}")
            
            print()  # Blank line between wallets
            await asyncio.sleep(0.5)  # Small delay between transactions
        
        # Final summary
        print(f"{'='*60}")
        print("CONSOLIDATION COMPLETE")
        print(f"{'='*60}")
        print(f"Successful transfers: {successful_transfers}")
        print(f"Total consolidated: {total_transferred:.6f} SOL")
        
        # Check wallet_0 final balance
        await asyncio.sleep(2)
        final_balance_resp = await client.get_balance(to_pubkey)
        final_balance = final_balance_resp.value / 1e9 if final_balance_resp.value else 0.0
        print(f"\nwallet_0 balance:")
        print(f"  Before: {initial_balance:.6f} SOL")
        print(f"  After:  {final_balance:.6f} SOL")
        print(f"  Gain:   +{final_balance - initial_balance:.6f} SOL")
        
        return successful_transfers > 0
        
    except Exception as e:
        print(f"\n[ERROR] Consolidation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(consolidate_to_wallet0())
    
    if success:
        print("\n[OK] Consolidation complete! wallet_0 is now funded.")
    else:
        print("\n[INFO] No funds were consolidated.")

