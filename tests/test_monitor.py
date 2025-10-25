"""
Unit tests for monitoring logic
Tests MC tracking, stall detection, abort triggers
"""

import pytest
import sys
import os
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMonitor:
    """Test monitoring and abort logic"""
    
    def test_stall_detection(self):
        """Test stall detection after 5 minutes"""
        from config import STALL_TIMEOUT
        
        # Simulate MC progression
        initial_mc = 1000  # $1K
        current_mc = 1400  # $1.4K
        elapsed_time = 310  # 5+ minutes
        
        # Growth check
        mc_growth = current_mc - initial_mc  # $400
        growth_threshold = initial_mc * 0.5  # 50% = $500
        
        is_stalled = mc_growth < growth_threshold and elapsed_time > STALL_TIMEOUT
        
        assert is_stalled, "Should detect stall (<50% growth in 5+ mins)"
        assert STALL_TIMEOUT == 300
    
    def test_threshold_trigger(self):
        """Test auto-rug trigger at $69K MC"""
        from config import RUG_THRESHOLD_MC
        
        # Simulate MC reaching threshold
        current_mc = 69420
        
        should_rug = current_mc >= RUG_THRESHOLD_MC
        
        assert should_rug
        assert RUG_THRESHOLD_MC == 69000
    
    def test_volume_check(self):
        """Test minimum volume requirement"""
        from config import MIN_REAL_VOLUME
        
        # Simulate real buyer volume
        real_volume_sol = 0.03  # 0.03 SOL
        
        sufficient_volume = real_volume_sol >= MIN_REAL_VOLUME
        
        assert not sufficient_volume, "0.03 SOL is less than 0.05 threshold"
        
        # Test with sufficient volume
        real_volume_sol = 0.08
        sufficient_volume = real_volume_sol >= MIN_REAL_VOLUME
        
        assert sufficient_volume
    
    def test_monitoring_interval(self):
        """Test monitoring interval is optimized"""
        from config import WASH_INTERVAL
        
        # Should be 30s (reduced from 60s)
        assert WASH_INTERVAL == 30
        
        # Calculate checks per 5 minutes
        checks_per_5min = 300 / WASH_INTERVAL
        
        assert checks_per_5min == 10  # 10 checks in 5 minutes
    
    def test_wash_trade_trigger(self):
        """Test wash trades only trigger when needed"""
        # Only trigger wash trades if MC < $5K
        mc = 3000
        cycle_count = 10
        
        should_wash = (cycle_count % 10 == 0) and (mc < 5000)
        
        assert should_wash
        
        # Don't wash if MC is higher
        mc = 10000
        should_wash = (cycle_count % 10 == 0) and (mc < 5000)
        
        assert not should_wash

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

