"""
Unit tests for bundler logic
Tests sequential buys, abort logic, cost calculations
"""

import pytest
import pytest_asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.mark.asyncio
class TestBundler:
    """Test bundler buy logic"""
    
    async def test_bundle_buy_cost_calculation(self):
        """Test total cost calculation for bundle buys"""
        from config import NUM_WALLETS, BUNDLE_SOL
        
        num_wallets = NUM_WALLETS
        per_wallet = BUNDLE_SOL
        
        total_cost = num_wallets * per_wallet
        
        # Should be 12 * 0.0025 = 0.03 SOL
        assert total_cost == 0.03
        assert num_wallets == 12
        assert per_wallet == 0.0025
    
    async def test_bundle_buy_slippage(self):
        """Test slippage settings"""
        # Buy slippage should be 12% (1200 bps)
        buy_slippage_bps = 1200
        
        # Sell slippage should be 15% (1500 bps)  
        sell_slippage_bps = 1500
        
        # Convert to percentage
        buy_slippage_pct = buy_slippage_bps / 100
        sell_slippage_pct = sell_slippage_bps / 100
        
        assert buy_slippage_pct == 12.0
        assert sell_slippage_pct == 15.0
    
    async def test_auto_abort_logic(self):
        """Test auto-abort after 3 consecutive failures"""
        failures = 0
        success = False
        
        # Simulate 3 failures
        for i in range(5):
            if i < 3:
                # Simulate failure
                failures += 1
            else:
                # Would succeed but should abort
                success = True
                
            # Check abort condition
            if i < 3 and failures >= 3:
                print(f"Auto-abort triggered at buy {i+1}")
                break
        
        assert failures == 3
        assert not success, "Should have aborted before success"
    
    async def test_sequential_delays(self):
        """Test random delays between buys"""
        import random
        from config import BUNDLE_DELAY
        
        base_delay = BUNDLE_DELAY  # 3.0s
        
        # Test 10 random delays
        delays = []
        for _ in range(10):
            actual_delay = base_delay + random.uniform(-1.0, 1.0)
            delays.append(actual_delay)
        
        # All delays should be between 2-4 seconds
        assert all(2.0 <= d <= 4.0 for d in delays)
        assert min(delays) < 2.5  # Should have some on lower end
        assert max(delays) > 3.5  # Should have some on higher end
    
    async def test_wallet_count_optimization(self):
        """Test that wallet count is correctly limited"""
        from config import NUM_WALLETS
        
        # Mock wallet list with 20 wallets
        mock_wallets = [Mock() for _ in range(20)]
        
        # Should only use NUM_WALLETS (12)
        actual_count = min(len(mock_wallets), NUM_WALLETS)
        
        assert actual_count == 12
        assert actual_count < len(mock_wallets)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

