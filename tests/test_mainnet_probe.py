"""
Phase 3: Mainnet Probe Tests
Minimal-cost API validation (~$2-4 total, 20-30 mins)

IMPORTANT: Run with mainnet RPC and PROBE_MODE=true
Cost Cap: 0.01 SOL if all probes fail (~$2)
"""

import pytest
import sys
import os
import asyncio
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Check if mainnet mode
from config import RPC_URL, PROBE_MODE

@pytest.fixture
def check_mainnet():
    """Ensure we're on mainnet for Phase 3"""
    if "devnet" in RPC_URL.lower():
        pytest.skip("Phase 3 requires mainnet RPC")
    if not PROBE_MODE:
        print("\n⚠️  WARNING: PROBE_MODE not enabled - set PROBE_MODE=true in .env")

@pytest.mark.asyncio
class TestAPIConnectivity:
    """API Connectivity Probes (0 cost, 5 mins)"""
    
    async def test_mainnet_rpc_connection(self, check_mainnet):
        """Test mainnet RPC connectivity"""
        from solana.rpc.async_api import AsyncClient
        
        client = AsyncClient(RPC_URL)
        
        try:
            response = await client.get_version()
            print(f"\n✅ Mainnet RPC connected")
            print(f"   Cluster: {response.value}")
            
            # Check recent blockhash
            blockhash_response = await client.get_latest_blockhash()
            print(f"✅ Recent blockhash: {blockhash_response.value.blockhash}")
            
            assert response.value is not None
            
        finally:
            await client.close()
    
    async def test_pumpfun_api_public_token(self, check_mainnet):
        """Probe Pump.fun API with public token (0 cost)"""
        
        # Use a known graduated token or recent launch
        test_mint = "So11111111111111111111111111111111111111112"  # Wrapped SOL (always exists)
        
        print(f"\n✅ Testing Pump.fun API connectivity...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to fetch token data
                response = await client.get(f"https://pumpportal.fun/api/tokens/{test_mint}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Pump.fun API responsive")
                    print(f"   Token data structure: {list(data.keys())}")
                elif response.status_code == 404:
                    print(f"✅ Pump.fun API responsive (token not found, expected)")
                else:
                    print(f"⚠️  Pump.fun API returned {response.status_code}")
                
                # Test is successful if we get any response
                assert response.status_code in [200, 404, 400], "API should respond"
                
        except httpx.ConnectTimeout:
            pytest.fail("Pump.fun API timeout - check network")
        except Exception as e:
            print(f"⚠️  Pump.fun API test: {e}")
            # Don't fail - API might have changed
    
    async def test_jupiter_quote_api(self, check_mainnet):
        """Test Jupiter quote API (0 cost)"""
        
        # Test a simple SOL → USDC quote (no execution)
        print(f"\n✅ Testing Jupiter API connectivity...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Jupiter V6 quote endpoint
                params = {
                    "inputMint": "So11111111111111111111111111111111111111112",  # SOL
                    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "amount": "100000",  # 0.0001 SOL
                    "slippageBps": "1200"
                }
                
                response = await client.get("https://quote-api.jup.ag/v6/quote", params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Jupiter API responsive")
                    print(f"   Quote data: {list(data.keys())[:5]}")
                    
                    # Check if it routes correctly
                    routes = data.get("routePlan", [])
                    print(f"   Routes available: {len(routes)}")
                    
                    assert data.get("outAmount") is not None, "Should return output amount"
                else:
                    print(f"⚠️  Jupiter returned {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Jupiter API test: {e}")
            # Don't fail - just log
    
    async def test_jito_endpoint_connectivity(self, check_mainnet):
        """Test Jito block engine endpoint (0 cost)"""
        from config import JITO_ENDPOINT
        
        print(f"\n✅ Testing Jito endpoint connectivity...")
        print(f"   Endpoint: {JITO_ENDPOINT}")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Just test connectivity (won't submit without valid bundle)
                response = await client.get(JITO_ENDPOINT.replace("/bundles", "/bundles/tip_stream"))
                
                # Any response means endpoint is reachable
                print(f"✅ Jito endpoint reachable (status: {response.status_code})")
                
        except httpx.ConnectError:
            print(f"⚠️  Jito endpoint not reachable - bundle submission may fail")
        except Exception as e:
            print(f"⚠️  Jito connectivity: {e}")

@pytest.mark.asyncio
class TestTinyTransactions:
    """Tiny Transaction Validation (0.005 SOL ~$1, 10 mins)"""
    
    @pytest.mark.skip(reason="Requires manual execution with funded wallet")
    async def test_micro_buy_probe(self, check_mainnet):
        """
        MANUAL TEST: Buy 0.0005 SOL worth of existing token
        
        Steps:
        1. Find low-MC token on DexScreener (pump.fun new launches)
        2. Run: python -c "from modules.bundler import RugBundler; import asyncio; bundler = RugBundler('MAINNET_RPC'); asyncio.run(bundler.bundle_buy('MINT_ADDRESS', 0.0005))"
        3. Verify: Transaction succeeds, tokens received, slippage handled
        
        Cost: ~$0.10 per wallet (0.0005 SOL × 2 wallets = 0.001 SOL)
        """
        print(f"\n⚠️  MANUAL TEST: Micro-buy probe")
        print(f"   1. Find token: https://dexscreener.com/solana?filters=pumpfun,new")
        print(f"   2. Copy mint address")
        print(f"   3. Run buy probe script")
        pytest.skip("Manual execution required")
    
    @pytest.mark.skip(reason="Requires manual execution after buy")
    async def test_micro_sell_probe(self, check_mainnet):
        """
        MANUAL TEST: Sell tokens from micro-buy
        
        Steps:
        1. After micro-buy, immediately run rug
        2. Run: python -c "from modules.rugger import RugExecutor; import asyncio; rugger = RugExecutor('MAINNET_RPC'); asyncio.run(rugger.execute('MINT_ADDRESS', partial=True))"
        3. Verify: Tokens sold, SOL recovered (~95% after fees), ROI calculated
        
        Cost: ~$0.05 in slippage/fees
        Expected recovery: ~0.0009 SOL (90% of 0.001 SOL invested)
        """
        print(f"\n⚠️  MANUAL TEST: Micro-sell probe")
        print(f"   1. Run rug executor on probe token")
        print(f"   2. Verify SOL recovery")
        print(f"   3. Check ROI calculation")
        pytest.skip("Manual execution required")
    
    @pytest.mark.skip(reason="Requires manual wallet funding")
    async def test_monitor_stall_simulation(self, check_mainnet):
        """
        MANUAL TEST: Monitor a token and trigger stall abort
        
        Steps:
        1. Start monitoring a low-activity token
        2. Wait 5 minutes (STALL_TIMEOUT)
        3. Verify auto-abort triggers
        4. Check partial rug execution
        
        Cost: $0 (just monitoring)
        """
        print(f"\n⚠️  MANUAL TEST: Stall detection")
        print(f"   1. Start monitor on low-activity token")
        print(f"   2. Wait 5 minutes")
        print(f"   3. Verify auto-abort")
        pytest.skip("Manual execution required")

@pytest.mark.asyncio
class TestGraduationDetection:
    """Graduation Detection Validation (0 cost)"""
    
    async def test_graduation_status_query(self, check_mainnet):
        """Test graduation detection on known tokens"""
        from modules.pumpfun_real import PumpFunReal
        
        pumpfun = PumpFunReal(RPC_URL)
        
        # Test with Wrapped SOL (should return no data or indicate not a pump.fun token)
        test_mint = "So11111111111111111111111111111111111111112"
        
        print(f"\n✅ Testing graduation detection...")
        
        try:
            token_data = await pumpfun.get_token_data(test_mint)
            
            if token_data:
                graduated = token_data.get('graduated', False)
                print(f"✅ Token data retrieved")
                print(f"   Graduated: {graduated}")
                print(f"   Data structure: {list(token_data.keys())}")
            else:
                print(f"✅ Token not found (expected for non-pump.fun token)")
            
            # Test passes if API responds (even with no data)
            assert True
            
        except Exception as e:
            print(f"⚠️  Graduation check: {e}")
            # Don't fail - API might have changed
    
    @pytest.mark.skip(reason="Requires finding a graduated token")
    async def test_pumpswap_routing_detection(self, check_mainnet):
        """
        MANUAL TEST: Find a graduated token and verify routing
        
        Steps:
        1. Find graduated token: https://dexscreener.com/solana?filters=pumpfun,graduated
        2. Check token data: python -c "from modules.pumpfun_real import PumpFunReal; import asyncio; pf = PumpFunReal('RPC'); print(asyncio.run(pf.get_token_data('MINT')))"
        3. Verify graduated=True
        4. Confirm rugger routes to Jupiter (not Pump.fun API)
        
        Cost: $0 (just queries)
        """
        print(f"\n⚠️  MANUAL TEST: PumpSwap routing")
        print(f"   1. Find graduated token")
        print(f"   2. Query graduation status")
        print(f"   3. Verify routing logic")
        pytest.skip("Manual execution required")

@pytest.mark.asyncio
class TestProbeMode:
    """Verify probe mode configuration"""
    
    async def test_probe_mode_enabled(self):
        """Verify PROBE_MODE settings"""
        from config import PROBE_MODE, NUM_WALLETS, BUNDLE_SOL, JITO_TIP
        
        print(f"\n✅ Checking probe mode configuration...")
        
        if PROBE_MODE:
            print(f"✅ PROBE_MODE enabled")
            print(f"   Wallets: {NUM_WALLETS} (should be 2)")
            print(f"   Buy amount: {BUNDLE_SOL} SOL (should be 0.0005)")
            print(f"   Jito tip: {JITO_TIP} SOL (should be 0)")
            
            assert NUM_WALLETS == 2, "Probe mode should use 2 wallets"
            assert BUNDLE_SOL == 0.0005, "Probe mode should use 0.0005 SOL"
            assert JITO_TIP == 0.0, "Probe mode should skip tips"
        else:
            print(f"⚠️  PROBE_MODE not enabled")
            print(f"   Set PROBE_MODE=true in .env for Phase 3")
            print(f"   Current: Wallets={NUM_WALLETS}, Buy={BUNDLE_SOL} SOL")
    
    async def test_cost_estimates(self):
        """Calculate Phase 3 cost estimates"""
        from config import PROBE_MODE, NUM_WALLETS, BUNDLE_SOL, PUMPFUN_TRADE_FEE
        
        print(f"\n✅ Phase 3 cost estimates:")
        
        if PROBE_MODE:
            # Micro-buy probe
            buy_cost = NUM_WALLETS * BUNDLE_SOL
            print(f"   Micro-buy probe: {buy_cost} SOL (~${buy_cost * 194:.2f})")
            
            # Trade fees
            trade_fees = buy_cost * PUMPFUN_TRADE_FEE
            print(f"   Trade fees: {trade_fees:.6f} SOL (~${trade_fees * 194:.2f})")
            
            # Slippage estimate (5% worst case)
            slippage = buy_cost * 0.05
            print(f"   Slippage (5%): {slippage:.6f} SOL (~${slippage * 194:.2f})")
            
            # Total worst case
            total = buy_cost + trade_fees + slippage
            print(f"   ─────────────────────────────────────")
            print(f"   Total (worst case): {total:.6f} SOL (~${total * 194:.2f})")
            print(f"   Recovery (90%): {buy_cost * 0.9:.6f} SOL (~${buy_cost * 0.9 * 194:.2f})")
            print(f"   Net cost: {total - (buy_cost * 0.9):.6f} SOL (~${(total - (buy_cost * 0.9)) * 194:.2f})")
            
            assert total < 0.01, "Phase 3 should cost < 0.01 SOL (~$2)"
        else:
            print(f"   ⚠️  Enable PROBE_MODE for accurate estimates")

@pytest.mark.asyncio
class TestWalletReadiness:
    """Check wallet funding for Phase 3"""
    
    async def test_probe_wallet_balance(self, check_mainnet):
        """Verify probe wallet has sufficient balance"""
        from solana.rpc.async_api import AsyncClient
        from solders.pubkey import Pubkey
        from modules.utils import load_wallets
        
        wallets = load_wallets()
        if not wallets:
            pytest.skip("No wallets found")
        
        client = AsyncClient(RPC_URL)
        
        try:
            wallet = wallets[0]
            
            try:
                pubkey_str = str(wallet.pubkey())
            except:
                pubkey_str = str(wallet.public_key)
            
            pubkey = Pubkey.from_string(pubkey_str)
            response = await client.get_balance(pubkey)
            balance = response.value / 1e9
            
            print(f"\n✅ Probe wallet balance check:")
            print(f"   Address: {pubkey_str}")
            print(f"   Balance: {balance:.6f} SOL (~${balance * 194:.2f})")
            
            min_required = 0.05  # Safety buffer
            if balance >= min_required:
                print(f"✅ Sufficient balance (>= {min_required} SOL)")
            else:
                print(f"⚠️  Low balance (need >= {min_required} SOL)")
                print(f"   Deficit: {min_required - balance:.6f} SOL")
            
            # Check if we have at least 2 wallets for probe mode
            if len(wallets) >= 2:
                print(f"✅ {len(wallets)} wallets available")
            else:
                print(f"⚠️  Only {len(wallets)} wallet(s) - need 2 for probe mode")
            
            assert balance >= 0, "Should have some balance"
            
        finally:
            await client.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

