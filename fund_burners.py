"""
Script to fund burner wallets from main wallet
Run this to distribute SOL to all 12 wallets for production
"""

import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import transfer, TransferParams
from modules.utils import load_wallets

async def fund_burners():
    wallets = load_wallets()
    
    if len(wallets) < 2:
        print("❌ Need at least 2 wallets (main + burners)")
        return
    
    main_wallet = wallets[0]
    burners = wallets[1:12]  # Fund up to 11 burners
    
    try:
        main_addr = str(main_wallet.pubkey())
    except:
        main_addr = str(main_wallet.public_key)
    
    rpc = 'https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1'
    client = AsyncClient(rpc)
    
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║           FUNDING BURNER WALLETS                          ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    try:
        # Check main wallet balance
        main_pubkey = Pubkey.from_string(main_addr)
        balance_response = await client.get_balance(main_pubkey)
        balance = balance_response.value / 1e9
        
        print(f"Main wallet: {main_addr}")
        print(f"Balance: {balance:.6f} SOL\n")
        
        # Calculate funding
        amount_per_wallet = 0.003  # 0.003 SOL per burner
        total_needed = amount_per_wallet * len(burners)
        
        if balance < total_needed + 0.01:  # +0.01 for fees and buffer
            print(f"⚠️  Insufficient balance!")
            print(f"   Need: {total_needed + 0.01:.6f} SOL")
            print(f"   Have: {balance:.6f} SOL")
            return
        
        print(f"Funding {len(burners)} burner wallets...")
        print(f"Amount per wallet: {amount_per_wallet} SOL")
        print(f"Total: {total_needed:.6f} SOL\n")
        
        funded = 0
        for i, burner in enumerate(burners, 1):
            try:
                try:
                    burner_addr = str(burner.pubkey())
                    burner_pubkey = burner.pubkey()
                except:
                    burner_addr = str(burner.public_key)
                    burner_pubkey = burner.public_key
                
                # Check if already funded
                burner_balance_response = await client.get_balance(Pubkey.from_string(burner_addr))
                burner_balance = burner_balance_response.value / 1e9
                
                if burner_balance >= amount_per_wallet:
                    print(f"  [{i}] ✅ Already funded: {burner_addr[:16]}... ({burner_balance:.6f} SOL)")
                    funded += 1
                    continue
                
                # Build transfer
                transfer_ix = transfer(
                    TransferParams(
                        from_pubkey=main_pubkey,
                        to_pubkey=Pubkey.from_string(burner_addr),
                        lamports=int(amount_per_wallet * 1e9)
                    )
                )
                
                # Get recent blockhash
                blockhash_response = await client.get_latest_blockhash()
                recent_blockhash = blockhash_response.value.blockhash
                
                # Build transaction
                tx = Transaction([transfer_ix], main_pubkey, recent_blockhash)
                
                # Sign
                tx.sign([main_wallet])
                
                # Send
                result = await client.send_raw_transaction(bytes(tx))
                
                if result.value:
                    print(f"  [{i}] ✅ Funded: {burner_addr[:16]}... TX: {str(result.value)[:16]}...")
                    funded += 1
                else:
                    print(f"  [{i}] ❌ Failed: {burner_addr[:16]}...")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"  [{i}] ❌ Error: {e}")
        
        print(f"\n✅ Funded {funded}/{len(burners)} wallets")
        print(f"   Total spent: ~{funded * amount_per_wallet:.6f} SOL")
        
        # Check final balance
        final_balance_response = await client.get_balance(main_pubkey)
        final_balance = final_balance_response.value / 1e9
        print(f"   Main wallet remaining: {final_balance:.6f} SOL\n")
        
    finally:
        await client.close()

if __name__ == '__main__':
    print("\n⚠️  WARNING: This will transfer real SOL on mainnet!")
    print("Continue? (y/n): ", end="")
    
    import sys
    if sys.stdin.isatty():
        response = input().strip().lower()
        if response != 'y':
            print("Cancelled")
            sys.exit(0)
    
    asyncio.run(fund_burners())

