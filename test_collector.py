"""
Test collector manually to see detailed errors
"""
import asyncio
from modules.collector import ProfitCollector
from bot_config import RPC_URL

async def test_collect():
    print("\n[TEST] Starting collector test...")
    
    collector = ProfitCollector(RPC_URL)
    
    print(f"[TEST] Collector enabled: {collector.enabled}")
    print(f"[TEST] Wallets loaded: {len(collector.wallets)}")
    
    if not collector.enabled:
        print("[ERROR] Collector disabled! Check MAIN_WALLET in Replit Secrets")
        return
    
    # Test preview first
    print("\n[TEST] Running preview...")
    preview = await collector.get_collection_preview()
    
    print("\n[TEST] Preview Result:")
    print(f"  Success: {preview['success']}")
    print(f"  Collectible: {preview.get('collectible', 0):.6f} SOL")
    print(f"  Wallets with funds: {preview.get('wallets_with_funds', 0)}")
    
    if not preview['success']:
        print(f"  Error: {preview.get('error', 'Unknown')}")
        print("\n[TEST] Preview failed - skipping collection")
        return
    
    if preview['collectible'] == 0:
        print("\n[TEST] No funds to collect - skipping collection")
        return
    
    print("\n[TEST] Running actual collection...")
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

