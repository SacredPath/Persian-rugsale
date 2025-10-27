"""
Transfer SOL between bot wallets (e.g., wallet_3 -> wallet_0)
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

async def transfer_between_wallets(from_index: int, to_index: int, amount_sol: float):
    """
    Transfer SOL from one bot wallet to another.
    
    Args:
        from_index: Source wallet index (e.g., 3 for wallet_3)
        to_index: Destination wallet index (e.g., 0 for wallet_0)
        amount_sol: Amount of SOL to transfer (e.g., 0.01)
    """
    try:
        print(f"\n[TRANSFER] Transferring {amount_sol} SOL from wallet_{from_index} to wallet_{to_index}...")
        
        # Load wallets
        wallets = load_wallets()
        if not wallets or len(wallets) <= max(from_index, to_index):
            print(f"[ERROR] Need at least {max(from_index, to_index) + 1} wallets!")
            return False
        
        from_wallet = wallets[from_index]
        to_wallet = wallets[to_index]
        
        from_addr = str(from_wallet.pubkey() if hasattr(from_wallet, 'pubkey') else from_wallet.public_key)
        to_addr = str(to_wallet.pubkey() if hasattr(to_wallet, 'pubkey') else to_wallet.public_key)
        
        print(f"[INFO] From wallet_{from_index}: {from_addr}")
        print(f"[INFO] To wallet_{to_index}: {to_addr}")
        
        # Check source wallet balance
        client = AsyncClient(RPC_URL)
        from_pubkey = Pubkey.from_string(from_addr)
        to_pubkey = Pubkey.from_string(to_addr)
        
        balance_resp = await client.get_balance(from_pubkey)
        balance_sol = balance_resp.value / 1e9 if balance_resp.value else 0.0
        print(f"[INFO] Source balance: {balance_sol:.6f} SOL")
        
        if balance_sol < amount_sol:
            print(f"[ERROR] Insufficient balance! Has {balance_sol:.6f} SOL, needs {amount_sol:.6f} SOL")
            return False
        
        # Calculate transfer amount
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
        
        # Import TxOpts for proper options format
        try:
            from solders.rpc.config import TxOpts
            from solders.commitment_config import CommitmentLevel
            tx_opts = TxOpts(
                skip_preflight=False,
                preflight_commitment=CommitmentLevel.Confirmed
            )
        except ImportError:
            # Fallback for older solana-py
            from solana.rpc.types import TxOpts
            from solana.rpc.commitment import Confirmed
            tx_opts = TxOpts(
                skip_preflight=False,
                preflight_commitment=Confirmed
            )
        
        send_result = await client.send_raw_transaction(
            bytes(tx),
            opts=tx_opts
        )
        
        if send_result.value:
            signature = str(send_result.value)
            print(f"\n[OK] TRANSFER SUCCESSFUL!")
            print(f"[INFO] Amount: {amount_sol} SOL")
            print(f"[INFO] TX: https://solscan.io/tx/{signature}")
            
            # Check new balances
            await asyncio.sleep(2)
            
            from_balance_resp = await client.get_balance(from_pubkey)
            from_balance_sol = from_balance_resp.value / 1e9 if from_balance_resp.value else 0.0
            
            to_balance_resp = await client.get_balance(to_pubkey)
            to_balance_sol = to_balance_resp.value / 1e9 if to_balance_resp.value else 0.0
            
            print(f"\n[INFO] NEW BALANCES:")
            print(f"  wallet_{from_index}: {from_balance_sol:.6f} SOL")
            print(f"  wallet_{to_index}: {to_balance_sol:.6f} SOL")
            
            return True
        else:
            print(f"[ERROR] Transaction failed!")
            return False
        
    except Exception as e:
        print(f"[ERROR] Transfer failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def show_wallet_balances():
    """Show balances of all bot wallets."""
    try:
        print("\n[INFO] Checking wallet balances...")
        wallets = load_wallets()
        if not wallets:
            print("[ERROR] No wallets found!")
            return
        
        client = AsyncClient(RPC_URL)
        
        print("\nWALLET BALANCES:")
        print("="*50)
        for i, wallet in enumerate(wallets):
            try:
                addr = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                pubkey = Pubkey.from_string(addr)
                balance_resp = await client.get_balance(pubkey)
                balance_sol = balance_resp.value / 1e9 if balance_resp.value else 0.0
                print(f"wallet_{i}: {balance_sol:.6f} SOL")
                print(f"  Address: {addr}")
            except Exception as e:
                print(f"wallet_{i}: ERROR - {e}")
        print("="*50)
        
    except Exception as e:
        print(f"[ERROR] Balance check failed: {e}")

if __name__ == "__main__":
    print("="*50)
    print("TRANSFER BETWEEN BOT WALLETS")
    print("="*50)
    
    # Show current balances
    asyncio.run(show_wallet_balances())
    
    # Get transfer details
    print("\nEnter source wallet index (0-3):")
    from_idx = int(input("From wallet_: ").strip())
    
    print("\nEnter destination wallet index (usually 0):")
    to_idx = int(input("To wallet_: ").strip())
    
    print("\nEnter amount to transfer (SOL):")
    amount = float(input("Amount: ").strip())
    
    # Confirm
    print(f"\n[WARNING] About to transfer {amount} SOL from wallet_{from_idx} to wallet_{to_idx}")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("[INFO] Transfer cancelled")
        exit(0)
    
    # Execute transfer
    success = asyncio.run(transfer_between_wallets(from_idx, to_idx, amount))
    
    if success:
        print("\n[OK] Transfer complete!")
        print("\n[INFO] Updated balances:")
        asyncio.run(show_wallet_balances())
    else:
        print("\n[ERROR] Transfer failed. Check errors above.")

