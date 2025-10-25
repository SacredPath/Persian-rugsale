"""
Unit tests for cost calculations
Validates optimization savings
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestCosts:
    """Test cost calculations and optimizations"""
    
    def test_per_cycle_cost(self):
        """Test total cost per cycle"""
        from config import PUMPFUN_CREATE_FEE, NUM_WALLETS, BUNDLE_SOL, JITO_TIP
        
        creation = PUMPFUN_CREATE_FEE  # 0.02
        buys = NUM_WALLETS * BUNDLE_SOL  # 12 * 0.0025 = 0.03
        tx_fees = 0.003  # Estimated
        priority = 0.002  # Estimated
        jito = JITO_TIP  # 0.0005
        
        total = creation + buys + tx_fees + priority + jito
        
        # Should be ~0.0555 SOL
        assert 0.05 <= total <= 0.06
        print(f"Total cost per cycle: {total:.4f} SOL")
    
    def test_optimization_savings(self):
        """Test cost reduction from optimizations"""
        # OLD values
        old_wallets = 20
        old_bundle_sol = 0.005
        old_jito_tip = 0.001
        old_cost = 0.02 + (old_wallets * old_bundle_sol) + 0.01 + old_jito_tip
        
        # NEW values
        from config import NUM_WALLETS, BUNDLE_SOL, JITO_TIP, PUMPFUN_CREATE_FEE
        new_cost = PUMPFUN_CREATE_FEE + (NUM_WALLETS * BUNDLE_SOL) + 0.005 + JITO_TIP
        
        savings = old_cost - new_cost
        savings_pct = (savings / old_cost) * 100
        
        assert savings > 0
        assert savings_pct > 50  # Should be ~56%
        print(f"Savings: {savings:.4f} SOL ({savings_pct:.1f}%)")
    
    def test_budget_impact(self):
        """Test how many cycles fit in 5 SOL budget"""
        from config import PUMPFUN_CREATE_FEE, NUM_WALLETS, BUNDLE_SOL, JITO_TIP
        
        budget = 5.0  # 5 SOL
        cost_per_cycle = PUMPFUN_CREATE_FEE + (NUM_WALLETS * BUNDLE_SOL) + 0.005 + JITO_TIP
        
        cycles = budget / cost_per_cycle
        
        # Should be ~90 cycles (vs 38 before)
        assert cycles > 80
        assert cycles < 100
        print(f"Cycles with 5 SOL: {cycles:.0f}")
    
    def test_break_even_calculation(self):
        """Test break-even point for profitability"""
        from config import PUMPFUN_CREATE_FEE, NUM_WALLETS, BUNDLE_SOL
        
        invested = PUMPFUN_CREATE_FEE + (NUM_WALLETS * BUNDLE_SOL)
        
        # Need at least 10% gain to break even with fees
        break_even_sol = invested * 1.1
        
        assert break_even_sol < 0.06
        print(f"Break-even: {break_even_sol:.4f} SOL ({break_even_sol/invested:.1f}x)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

