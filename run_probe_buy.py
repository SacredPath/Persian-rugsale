import asyncio
import sys
sys.path.insert(0, '.')

from modules.bundler import RugBundler

MINT = 'ENLKCZ7KGpPKajV4pcPhEfoo9zHyVBA8mtggzhPDpump'
RPC = 'https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1'

async def run_buy():
    print('\n[PROBE] Executing micro-buy probe...')
    print(f'[PROBE] Token: {MINT[:16]}...')
    print(f'[PROBE] Amount: 0.0005 SOL per wallet (2 wallets)')
    print(f'[PROBE] Total: 0.001 SOL (~$0.19)\n')
    
    bundler = RugBundler(RPC)
    
    try:
        result = await bundler.bundle_buy(MINT, amount=0.0005)
        
        if result:
            print('\n[PROBE] ✅ Micro-buy successful!')
            print('[PROBE] Tokens received in 2 wallets')
            return True
        else:
            print('\n[PROBE] ❌ Micro-buy failed')
            return False
    except Exception as e:
        print(f'\n[PROBE] ❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = asyncio.run(run_buy())
    print(f'\n[PROBE] Result: {"SUCCESS" if success else "FAILED"}')
    sys.exit(0 if success else 1)

