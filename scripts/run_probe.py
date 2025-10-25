#!/usr/bin/env python3
"""
Phase 3 Probe Runner
Quick script to execute mainnet probes with safety checks
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         PHASE 3: MAINNET PROBE RUNNER                     ║")
    print("║              ~$2-4 Budget, 20-30 Minutes                   ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    # Safety checks
    from config import RPC_URL, PROBE_MODE, NUM_WALLETS, BUNDLE_SOL, JITO_TIP
    from modules.utils import load_wallets
    
    print("[SAFETY] Pre-flight checks...")
    
    # Check 1: Mainnet RPC
    is_mainnet = "mainnet" in RPC_URL.lower()
    if not is_mainnet:
        print("❌ ERROR: Not using mainnet RPC")
        print(f"   Current: {RPC_URL}")
        print("\n[FIX] Update .env:")
        print("   SOLANA_RPC=https://api.mainnet-beta.solana.com")
        return 1
    
    print(f"✅ Mainnet RPC: {RPC_URL[:50]}...")
    
    # Check 2: Probe mode
    if not PROBE_MODE:
        print("⚠️  WARNING: PROBE_MODE not enabled!")
        print(f"   Current: Wallets={NUM_WALLETS}, Buy={BUNDLE_SOL} SOL, Tip={JITO_TIP} SOL")
        print("\n   Enable probe mode? (y/n): ", end="")
        
        response = input().strip().lower()
        if response != 'y':
            print("\n[FIX] Enable PROBE_MODE in .env:")
            print("   PROBE_MODE=true")
            return 1
    else:
        print(f"✅ Probe mode enabled")
        print(f"   Wallets: {NUM_WALLETS}, Buy: {BUNDLE_SOL} SOL, Tip: {JITO_TIP} SOL")
    
    # Check 3: Wallet balance
    wallets = load_wallets()
    if not wallets:
        print("❌ ERROR: No wallets found")
        print("\n[FIX] Generate wallets:")
        print("   python -c \"from modules.utils import generate_wallets; generate_wallets(12)\"")
        return 1
    
    print(f"✅ {len(wallets)} wallets loaded")
    
    # Check balance
    import asyncio
    from solana.rpc.async_api import AsyncClient
    from solders.pubkey import Pubkey
    
    async def check_balance():
        client = AsyncClient(RPC_URL)
        try:
            wallet = wallets[0]
            try:
                pubkey_str = str(wallet.pubkey())
            except:
                pubkey_str = str(wallet.public_key)
            
            pubkey = Pubkey.from_string(pubkey_str)
            response = await client.get_balance(pubkey)
            return response.value / 1e9, pubkey_str
        finally:
            await client.close()
    
    balance, address = asyncio.run(check_balance())
    
    print(f"   Address: {address[:16]}...")
    print(f"   Balance: {balance:.6f} SOL (~${balance * 194:.2f})")
    
    if balance < 0.02:
        print(f"\n⚠️  WARNING: Low balance (< 0.02 SOL)")
        print(f"   Recommended: >= 0.05 SOL for probes")
        print(f"\n   Continue anyway? (y/n): ", end="")
        
        response = input().strip().lower()
        if response != 'y':
            print("\n[FIX] Fund wallet:")
            print(f"   solana transfer {address} 0.05 --allow-unfunded-recipient")
            return 1
    else:
        print(f"✅ Sufficient balance")
    
    # Cost estimate
    print(f"\n[COST] Phase 3 estimates:")
    total_cost = NUM_WALLETS * BUNDLE_SOL * 1.1  # +10% for fees/slippage
    print(f"   Per probe: {NUM_WALLETS * BUNDLE_SOL} SOL (~${NUM_WALLETS * BUNDLE_SOL * 194:.2f})")
    print(f"   With fees: {total_cost:.6f} SOL (~${total_cost * 194:.2f})")
    print(f"   Recovery (~90%): {NUM_WALLETS * BUNDLE_SOL * 0.9:.6f} SOL")
    print(f"   Net cost: {total_cost - (NUM_WALLETS * BUNDLE_SOL * 0.9):.6f} SOL (~${(total_cost - (NUM_WALLETS * BUNDLE_SOL * 0.9)) * 194:.2f})")
    
    # Menu
    print("\n" + "="*60)
    print("PHASE 3 PROBE MENU")
    print("="*60)
    print("\n[AUTOMATIC TESTS]")
    print("  1. API Connectivity (0 cost, 5 mins)")
    print("     - Mainnet RPC check")
    print("     - Pump.fun API probe")
    print("     - Jupiter quote test")
    print("     - Jito endpoint check")
    
    print("\n[MANUAL PROBES]")
    print("  2. Micro-Buy Probe (~$0.19, find token first)")
    print("  3. Micro-Sell Probe (~$0.02, after buy)")
    print("  4. Graduation Check ($0, find graduated token)")
    
    print("\n[UTILITIES]")
    print("  5. Check wallet balance")
    print("  6. Find test token (open DexScreener)")
    print("  7. Exit")
    
    print("\n" + "="*60)
    print("Select option (1-7): ", end="")
    
    choice = input().strip()
    
    if choice == '1':
        print("\n[RUN] API Connectivity Tests...")
        os.system("pytest tests/test_mainnet_probe.py::TestAPIConnectivity -v -s")
    
    elif choice == '2':
        print("\n[MANUAL] Micro-Buy Probe")
        print("\nStep 1: Find low-MC token on DexScreener")
        print("   https://dexscreener.com/solana?filters=pumpfun,new,mc-10k")
        print("\nStep 2: Copy mint address")
        print("Enter mint address: ", end="")
        mint = input().strip()
        
        if len(mint) < 32:
            print("❌ Invalid mint address")
            return 1
        
        print(f"\n[EXECUTE] Buying {BUNDLE_SOL} SOL from {NUM_WALLETS} wallets...")
        print(f"Cost: {NUM_WALLETS * BUNDLE_SOL} SOL (~${NUM_WALLETS * BUNDLE_SOL * 194:.2f})")
        print("Confirm? (y/n): ", end="")
        
        if input().strip().lower() == 'y':
            from modules.bundler import RugBundler
            bundler = RugBundler(RPC_URL)
            asyncio.run(bundler.bundle_buy(mint, amount=BUNDLE_SOL))
        else:
            print("Cancelled")
    
    elif choice == '3':
        print("\n[MANUAL] Micro-Sell Probe")
        print("Enter mint address (from previous buy): ", end="")
        mint = input().strip()
        
        if len(mint) < 32:
            print("❌ Invalid mint address")
            return 1
        
        print(f"\n[EXECUTE] Selling tokens (partial rug = 50%)...")
        print("Confirm? (y/n): ", end="")
        
        if input().strip().lower() == 'y':
            from modules.rugger import RugExecutor
            rugger = RugExecutor(RPC_URL)
            asyncio.run(rugger.execute(mint, partial=True))
        else:
            print("Cancelled")
    
    elif choice == '4':
        print("\n[MANUAL] Graduation Check")
        print("Enter mint address (graduated token, MC > $69K): ", end="")
        mint = input().strip()
        
        if len(mint) < 32:
            print("❌ Invalid mint address")
            return 1
        
        from modules.pumpfun_real import PumpFunReal
        pumpfun = PumpFunReal(RPC_URL)
        data = asyncio.run(pumpfun.get_token_data(mint))
        
        if data:
            print(f"\n✅ Token data:")
            print(f"   Graduated: {data.get('graduated', False)}")
            print(f"   Market Cap: ${data.get('market_cap', 0):,.0f}")
            print(f"   Data: {list(data.keys())}")
        else:
            print("❌ Token not found or API error")
    
    elif choice == '5':
        print(f"\n[INFO] Wallet balance:")
        print(f"   Address: {address}")
        print(f"   Balance: {balance:.6f} SOL (~${balance * 194:.2f})")
    
    elif choice == '6':
        import webbrowser
        print("\n[OPEN] DexScreener...")
        webbrowser.open("https://dexscreener.com/solana?filters=pumpfun,new,mc-10k")
    
    elif choice == '7':
        print("\nExiting...")
        return 0
    
    else:
        print("❌ Invalid choice")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

