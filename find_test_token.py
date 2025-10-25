"""
Helper script to find a low-MC test token on Pump.fun for Phase 3 probe
"""

import requests
import time

print("\n" + "="*62)
print("  FINDING TEST TOKEN FOR PHASE 3 PROBE")
print("="*62 + "\n")

print("Searching for low-MC Pump.fun tokens on DexScreener...\n")

try:
    # DexScreener API for recent Solana tokens
    url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"
    
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        pairs = data.get('pairs', [])
        
        print(f"Found {len(pairs)} pairs\n")
        
        # Filter for pump.fun tokens with low MC
        pumpfun_tokens = []
        for pair in pairs[:20]:  # Check first 20
            dex = pair.get('dexId', '').lower()
            mc = pair.get('fdv', 0)
            
            if 'pump' in dex or 'raydium' in dex:
                if mc and mc < 50000:  # Under $50K MC
                    token_addr = pair.get('baseToken', {}).get('address')
                    token_name = pair.get('baseToken', {}).get('name', 'Unknown')
                    token_symbol = pair.get('baseToken', {}).get('symbol', 'UNK')
                    
                    pumpfun_tokens.append({
                        'address': token_addr,
                        'name': token_name,
                        'symbol': token_symbol,
                        'mc': mc,
                        'dex': dex
                    })
        
        if pumpfun_tokens:
            print("Found suitable test tokens:\n")
            for i, token in enumerate(pumpfun_tokens[:5], 1):
                print(f"{i}. {token['name']} (${token['symbol']})")
                print(f"   Address: {token['address']}")
                print(f"   MC: ${token['mc']:,.0f}")
                print(f"   DEX: {token['dex']}\n")
            
            print("="*62)
            print("  RECOMMENDED TOKEN FOR PROBE")
            print("="*62 + "\n")
            
            best = pumpfun_tokens[0]
            print(f"Token: {best['name']} (${best['symbol']})")
            print(f"Mint: {best['address']}")
            print(f"MC: ${best['mc']:,.0f}")
            print(f"\nCopy this mint address for the next step!\n")
            
        else:
            print("⚠️  No suitable tokens found via API\n")
            print("MANUAL OPTION:")
            print("1. Go to: https://dexscreener.com/solana")
            print("2. Filter: 'pumpfun', 'new', 'MC < $10K'")
            print("3. Pick any low-activity token")
            print("4. Copy the mint address\n")
    
    else:
        print(f"⚠️  DexScreener API returned {response.status_code}\n")
        print("MANUAL OPTION:")
        print("1. Go to: https://dexscreener.com/solana")
        print("2. Filter: 'pumpfun', 'new', 'MC < $10K'")
        print("3. Pick any low-activity token")
        print("4. Copy the mint address\n")

except Exception as e:
    print(f"⚠️  Error: {e}\n")
    print("MANUAL OPTION:")
    print("1. Go to: https://dexscreener.com/solana")
    print("2. Filter: 'pumpfun', 'new', 'MC < $10K'")
    print("3. Pick any low-activity token")
    print("4. Copy the mint address\n")

print("="*62)
print("\nNext: Use this mint address for micro-buy probe")
print("="*62 + "\n")

