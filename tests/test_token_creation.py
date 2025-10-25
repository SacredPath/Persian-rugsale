"""
Unit tests for token creation
Mocks Pump.fun API responses
"""

import pytest
import pytest_asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.mark.asyncio
class TestTokenCreation:
    """Test token creation with mocked Pump.fun API"""
    
    async def test_create_token_success(self):
        """Test successful token creation"""
        from modules.pumpfun_real import PumpFunReal
        
        pf = PumpFunReal("http://fake-rpc.com")
        
        # Mock the API response
        with patch('modules.pumpfun_real.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "mint": "FakeMint123ABC"
            }
            mock_response.raise_for_status = Mock()
            mock_response.status_code = 200
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Mock wallet
            mock_wallet = Mock()
            mock_wallet.pubkey.return_value = "FakeWalletPubkey"
            
            result = await pf.create_token(
                creator_wallet=mock_wallet,
                name="TestToken",
                symbol="TEST",
                description="Test token",
                image_url="http://test.com/image.png"
            )
            
            assert result == "FakeMint123ABC"
            mock_post.assert_called_once()
    
    async def test_create_token_api_failure(self):
        """Test token creation with API error"""
        from modules.pumpfun_real import PumpFunReal
        
        pf = PumpFunReal("http://fake-rpc.com")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"success": False, "error": "Insufficient funds"}
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            
            from httpx import HTTPStatusError, Request, Response
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Bad Request",
                request=Mock(spec=Request),
                response=Mock(spec=Response, status_code=400, text="Bad Request")
            )
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            mock_wallet = Mock()
            mock_wallet.pubkey.return_value = "FakeWalletPubkey"
            
            result = await pf.create_token(
                creator_wallet=mock_wallet,
                name="TestToken",
                symbol="TEST",
                description="Test",
                image_url="http://test.com/img.png"
            )
            
            # Should return None on failure
            assert result is None
    
    async def test_create_token_fee_calculation(self):
        """Test that creation fee is correctly accounted for"""
        from config import PUMPFUN_CREATE_FEE
        
        # Verify fee is set to 0.02 SOL
        assert PUMPFUN_CREATE_FEE == 0.02
        
        # Mock wallet with balance check
        mock_wallet_balance = 0.05  # 0.05 SOL
        required_fee = PUMPFUN_CREATE_FEE
        
        # Simulate fee deduction
        remaining = mock_wallet_balance - required_fee
        
        assert abs(remaining - 0.03) < 0.0001  # Floating point tolerance
        assert remaining > 0, "Insufficient balance for creation fee"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

