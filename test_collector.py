"""
Test collector manually to see detailed errors
"""
import asyncio
from modules.collector import ProfitCollector
from config import RPC_URL

async def test_collect():
    print("\n[TEST] Starting collector test...")
    
    collector = ProfitCollector(RPC_URL)
    
    print(f"[TEST] Collector enabled: {collector.enabled}")
    print(f"[TEST] Wallets loaded: {len(collector.wallets)}")
    
    if not collector.enabled:
        print("[ERROR] Collector disabled! Check MAIN_WALLET in Replit Secrets")
        return
    
    print("\n[TEST] Running collection...")
    result = await collector.collect_all()
    
    print("\n[TEST] Result:")
    print(f"  Success: {result['success']}")
    print(f"  Collected: {result.get('collected', 0):.6f} SOL")
    print(f"  Transferred: {result.get('transferred', 0)}")
    print(f"  Failed: {result.get('failed', 0)}")
    
    if not result['success']:
        print(f"  Error: {result.get('error', 'Unknown')}")
    
    print("\n[TEST] Details:")
    for detail in result.get('details', []):
        print(f"  Wallet {detail.get('wallet', '?')}: {detail.get('status', 'unknown')}")
        if 'reason' in detail:
            print(f"    Reason: {detail['reason']}")
        if 'amount' in detail:
            print(f"    Amount: {detail['amount']:.6f} SOL")

if __name__ == "__main__":
    asyncio.run(test_collect())

