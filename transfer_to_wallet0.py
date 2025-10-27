"""
Transfer SOL from an external wallet to wallet_0
"""
import asyncio
from solana.rpc.async_api import AsyncClient
from bot_config import RPC_URL
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

async def transfer_sol_to_wallet0(from_private_key: str, amount_sol: float):
    """
    Transfer SOL from an external wallet to wallet_0.
    
    Args:
        from_private_key: Private key of source wallet (base58 string or JSON array)
        amount_sol: Amount of SOL to transfer (e.g., 0.01)
    """
    try:
        print(f"\n[TRANSFER] Transferring {amount_sol} SOL to wallet_0...")
        
        # Load wallet_0
        wallets = load_wallets()
        if not wallets or len(wallets) == 0:
            print("[ERROR] No wallets found! Generate wallets first.")
            return False
        
        wallet_0 = wallets[0]
        wallet_0_addr = str(wallet_0.pubkey() if hasattr(wallet_0, 'pubkey') else wallet_0.public_key)
        print(f"[INFO] wallet_0 address: {wallet_0_addr}")
        
        # Parse source wallet private key
        print(f"[INFO] Loading source wallet...")
        try:
            # Try parsing as JSON array first (e.g., [1,2,3,...])
            import json
            if from_private_key.strip().startswith('['):
                key_bytes = bytes(json.loads(from_private_key))
                from_wallet = Keypair.from_bytes(key_bytes)
            else:
                # Try as base58 string
                import base58
                key_bytes = base58.b58decode(from_private_key)
                from_wallet = Keypair.from_bytes(key_bytes)
        except Exception as e:
            print(f"[ERROR] Invalid private key format: {e}")
            print("[INFO] Expected format: base58 string or JSON array like [1,2,3,...]")
            return False
        
        from_wallet_addr = str(from_wallet.pubkey() if hasattr(from_wallet, 'pubkey') else from_wallet.public_key)
        print(f"[INFO] Source wallet address: {from_wallet_addr}")
        
        # Check source wallet balance
        client = AsyncClient(RPC_URL)
        from_pubkey = Pubkey.from_string(from_wallet_addr)
        to_pubkey = Pubkey.from_string(wallet_0_addr)
        
        balance_resp = await client.get_balance(from_pubkey)
        balance_sol = balance_resp.value / 1e9 if balance_resp.value else 0.0
        print(f"[INFO] Source balance: {balance_sol:.6f} SOL")
        
        if balance_sol < amount_sol:
            print(f"[ERROR] Insufficient balance! Has {balance_sol:.6f} SOL, needs {amount_sol:.6f} SOL")
            return False
        
        # Calculate transfer amount (leave 0.000005 SOL for fees)
        transfer_lamports = int(amount_sol * 1e9)
        
        # Get recent blockhash
        print(f"[INFO] Building transfer transaction...")
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
            tx = VersionedTransaction(message, [from_wallet])
        else:
            tx = Transaction()
            tx.recent_blockhash = recent_blockhash
            tx.add(transfer_ix)
            tx.sign(from_wallet)
        
        # Send transaction
        print(f"[INFO] Sending transaction...")
        send_result = await client.send_raw_transaction(
            bytes(tx),
            opts={"skipPreflight": False, "preflightCommitment": "confirmed"}
        )
        
        if send_result.value:
            signature = str(send_result.value)
            print(f"\n[OK] TRANSFER SUCCESSFUL!")
            print(f"[INFO] Amount: {amount_sol} SOL")
            print(f"[INFO] From: {from_wallet_addr}")
            print(f"[INFO] To: {wallet_0_addr}")
            print(f"[INFO] TX: https://solscan.io/tx/{signature}")
            
            # Check new balances
            await asyncio.sleep(2)
            new_balance_resp = await client.get_balance(to_pubkey)
            new_balance_sol = new_balance_resp.value / 1e9 if new_balance_resp.value else 0.0
            print(f"\n[INFO] wallet_0 new balance: {new_balance_sol:.6f} SOL")
            
            return True
        else:
            print(f"[ERROR] Transaction failed!")
            return False
        
    except Exception as e:
        print(f"[ERROR] Transfer failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*50)
    print("SOL TRANSFER TO WALLET_0")
    print("="*50)
    
    # Get private key from user
    print("\nEnter source wallet private key:")
    print("  Format 1: Base58 string (e.g., 5Jx7...)")
    print("  Format 2: JSON array (e.g., [1,2,3,4,5,...])")
    print()
    from_key = input("Private key: ").strip()
    
    # Get amount
    print("\nEnter amount to transfer (SOL):")
    amount = float(input("Amount: ").strip())
    
    # Confirm
    print(f"\n[WARNING] About to transfer {amount} SOL to wallet_0")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("[INFO] Transfer cancelled")
        exit(0)
    
    # Execute transfer
    success = asyncio.run(transfer_sol_to_wallet0(from_key, amount))
    
    if success:
        print("\n[OK] Transfer complete! wallet_0 is now funded.")
    else:
        print("\n[ERROR] Transfer failed. Check errors above.")

