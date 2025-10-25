import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

async def check_balance():
    addr = 'FLeDqdHg1TzG5x3Sjd1Q6sdUAqUzpEZuw1VnXHPm88Nj'
    rpc = 'https://mainnet.helius-rpc.com/?api-key=4d72947c-31b4-4821-8b7b-cef17cd1eba1'
    client = AsyncClient(rpc)
    
    try:
        print('\n' + '='*62)
        print('  CHECKING MAINNET BALANCE...')
        print('='*62 + '\n')
        
        pubkey = Pubkey.from_string(addr)
        response = await client.get_balance(pubkey)
        balance = response.value / 1e9
        balance_usd = balance * 194
        
        print(f'Wallet: {addr}')
        print(f'Balance: {balance:.6f} SOL (${balance_usd:.2f})\n')
        
        min_required = 0.05
        if balance >= min_required:
            print('='*62)
            print('  ✅ STATUS: READY FOR PHASE 3')
            print('='*62)
            print('\n✅ Sufficient balance for all probes!')
            print(f'   Available: {balance:.6f} SOL')
            print(f'   Required: {min_required} SOL')
            print(f'   Buffer: {balance - min_required:.6f} SOL\n')
            print('Phase 3 will cost approximately:')
            print('  • API tests: $0')
            print('  • Micro-buy: 0.001 SOL (~$0.19)')
            print('  • Micro-sell: Recovery ~0.0009 SOL (~90%)')
            print('  • Net cost: ~0.0001 SOL (~$0.02)\n')
            print('='*62)
            print('  🚀 READY TO START')
            print('='*62)
            print('\nSay "start phase 3" to begin testing!\n')
            return True
            
        elif balance > 0.002:
            print('='*62)
            print('  ⚠️  STATUS: PARTIAL READINESS')
            print('='*62)
            print(f'\nCurrent balance: {balance:.6f} SOL')
            print(f'Can run: {int(balance / 0.001)} micro-probes')
            print(f'Need: {min_required - balance:.6f} SOL more for full testing\n')
            print('Options:')
            print('  1. Add more SOL (recommended)')
            print('  2. Say "start anyway" for limited testing\n')
            return False
            
        else:
            print('='*62)
            print('  ❌ STATUS: NOT FUNDED YET')
            print('='*62)
            print(f'\nBalance: {balance:.6f} SOL')
            print(f'Need: {min_required - balance:.6f} SOL (~${(min_required - balance) * 194:.2f})\n')
            print('Please fund your Phantom wallet and run "check balance" again.\n')
            return False
        
    finally:
        await client.close()

if __name__ == '__main__':
    asyncio.run(check_balance())

