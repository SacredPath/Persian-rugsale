"""
Pytest configuration and shared fixtures
"""

import pytest
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_wallet():
    """Create a mock wallet for testing"""
    from unittest.mock import Mock
    
    wallet = Mock()
    wallet.pubkey.return_value = "MockWalletPubkey123ABC"
    wallet.public_key = "MockWalletPubkey123ABC"
    return wallet

@pytest.fixture
def mock_token_mint():
    """Create a mock token mint address"""
    return "MockTokenMint456DEF"

@pytest.fixture
def mock_rpc_url():
    """Mock RPC URL"""
    return "http://localhost:8899"

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "NUM_WALLETS": 12,
        "BUNDLE_SOL": 0.0025,
        "JITO_TIP": 0.0005,
        "STALL_TIMEOUT": 300,
        "MIN_REAL_VOLUME": 0.05,
        "RUG_THRESHOLD_MC": 69000
    }

