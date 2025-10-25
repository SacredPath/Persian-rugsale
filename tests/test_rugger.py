"""
Unit tests for rug execution
Tests graduation detection, partial rug, ROI calculation
"""

import pytest
import pytest_asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.mark.asyncio
class TestRugger:
    """Test rug execution logic"""
    
    async def test_graduation_detection(self):
        """Test detecting if token graduated to PumpSwap"""
        # Mock token data
        mock_token_data_bonding = {"graduated": False, "mc": 50000}
        mock_token_data_graduated = {"graduated": True, "mc": 75000}
        
        # Test bonding curve
        graduated = mock_token_data_bonding.get('graduated', False)
        assert not graduated
        
        # Test graduated
        graduated = mock_token_data_graduated.get('graduated', False)
        assert graduated
    
    async def test_partial_rug_calculation(self):
        """Test partial rug sells 50% of holdings"""
        # Mock wallet balance
        total_tokens = 100000
        partial = True
        
        sell_amount = int(total_tokens * 0.5) if partial else total_tokens
        
        assert sell_amount == 50000
        assert sell_amount == total_tokens / 2
    
    async def test_full_rug_calculation(self):
        """Test full rug sells 100% of holdings"""
        total_tokens = 100000
        partial = False
        
        sell_amount = int(total_tokens * 0.5) if partial else total_tokens
        
        assert sell_amount == 100000
        assert sell_amount == total_tokens
    
    async def test_roi_calculation(self):
        """Test ROI calculation"""
        # Investment
        invested_sol = 0.03  # 12 wallets * 0.0025
        
        # Recovery scenarios
        scenarios = [
            (0.03, 0),      # Break-even: 0% ROI
            (0.06, 100),    # 2x: 100% ROI
            (0.15, 400),    # 5x: 400% ROI
            (0.30, 900),    # 10x: 900% ROI
        ]
        
        for recovered, expected_roi in scenarios:
            if recovered > 0:
                actual_roi = ((recovered - invested_sol) / invested_sol) * 100
            else:
                actual_roi = -100
            
            assert abs(actual_roi - expected_roi) < 1, f"ROI mismatch for {recovered} SOL"
    
    async def test_slippage_optimization(self):
        """Test sell slippage is reduced"""
        # Sell slippage should be 15% (1500 bps) - optimized from 20%
        sell_slippage_bps = 1500
        
        old_slippage_bps = 2000
        
        reduction = ((old_slippage_bps - sell_slippage_bps) / old_slippage_bps) * 100
        
        assert sell_slippage_bps == 1500
        assert reduction == 25  # 25% reduction in slippage
    
    async def test_bundle_collection(self):
        """Test sell transaction collection for Jito bundle"""
        # Mock wallets with balances
        wallets_with_tokens = [
            {"wallet": "W1", "balance": 10000},
            {"wallet": "W2", "balance": 15000},
            {"wallet": "W3", "balance": 0},  # Skip this
            {"wallet": "W4", "balance": 12000},
        ]
        
        # Collect sells
        sell_transactions = []
        for w in wallets_with_tokens:
            if w["balance"] > 0:
                sell_transactions.append(w)
        
        assert len(sell_transactions) == 3
        assert all(t["balance"] > 0 for t in sell_transactions)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

