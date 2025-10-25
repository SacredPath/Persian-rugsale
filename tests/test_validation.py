"""
Unit tests for input validation
Tests /launch command parsing and validation logic
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def validate_launch(name, symbol, image_url):
    """Validation logic from main.py"""
    if len(name) > 32:
        raise ValueError("Token name too long (max 32 chars)")
    if len(symbol) > 10:
        raise ValueError("Symbol too long (max 10 chars)")
    if not image_url.startswith('http'):
        raise ValueError("Invalid image URL (must start with http)")
    return True

class TestValidation:
    """Test input validation for /launch command"""
    
    def test_valid_launch(self):
        """Test valid inputs pass validation"""
        assert validate_launch("DogeCoin", "DOGE", "http://example.com/logo.png") == True
        assert validate_launch("A", "B", "https://test.com/img.jpg") == True
    
    def test_invalid_name_too_long(self):
        """Test name longer than 32 chars fails"""
        with pytest.raises(ValueError, match="Token name too long"):
            validate_launch("A" * 33, "DOGE", "http://example.com/logo.png")
    
    def test_invalid_symbol_too_long(self):
        """Test symbol longer than 10 chars fails"""
        with pytest.raises(ValueError, match="Symbol too long"):
            validate_launch("DogeCoin", "VERYLONGSYM", "http://example.com/logo.png")
    
    def test_invalid_url_no_http(self):
        """Test URL without http fails"""
        with pytest.raises(ValueError, match="Invalid image URL"):
            validate_launch("DogeCoin", "DOGE", "example.com/logo.png")
        
        with pytest.raises(ValueError, match="Invalid image URL"):
            validate_launch("DogeCoin", "DOGE", "ftp://example.com/logo.png")
    
    def test_edge_cases(self):
        """Test boundary conditions"""
        # Exactly 32 chars - should pass
        assert validate_launch("A" * 32, "DOGE", "http://test.com") == True
        
        # Exactly 10 chars - should pass
        assert validate_launch("Test", "A" * 10, "http://test.com") == True
        
        # Empty strings - should fail on URL
        with pytest.raises(ValueError):
            validate_launch("", "", "")
    
    def test_config_values(self):
        """Test optimized config values are correct"""
        from config import NUM_WALLETS, BUNDLE_SOL, JITO_TIP, STALL_TIMEOUT
        
        assert NUM_WALLETS == 12, f"NUM_WALLETS should be 12, got {NUM_WALLETS}"
        assert BUNDLE_SOL == 0.0025, f"BUNDLE_SOL should be 0.0025, got {BUNDLE_SOL}"
        assert JITO_TIP == 0.0005, f"JITO_TIP should be 0.0005, got {JITO_TIP}"
        assert STALL_TIMEOUT == 300, f"STALL_TIMEOUT should be 300, got {STALL_TIMEOUT}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

