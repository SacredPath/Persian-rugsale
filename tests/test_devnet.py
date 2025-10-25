"""
Phase 2: Devnet Integration Tests
Tests real blockchain interactions with free devnet SOL
"""

import pytest
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.mark.asyncio
class TestDevnetRPC:
    """Test RPC connection and blockchain queries"""
    
    async def test_rpc_connection(self):
        """Test connection to Solana devnet"""
        from solana.rpc.async_api import AsyncClient
        
        rpc_url = "https://api.devnet.solana.com"
        client = AsyncClient(rpc_url)
        
        try:
            # Get cluster version
            response = await client.get_version()
            print(f"\n✅ Connected to Solana devnet")
            print(f"   Cluster version: {response.value}")
            
            assert response.value is not None
            
            # Get recent blockhash
            blockhash_response = await client.get_latest_blockhash()
            print(f"✅ Recent blockhash: {blockhash_response.value.blockhash}")
            
            assert blockhash_response.value is not None
            
        finally:
            await client.close()
    
    async def test_get_balance(self):
        """Test querying SOL balance"""
        from solana.rpc.async_api import AsyncClient
        from solders.pubkey import Pubkey
        
        rpc_url = "https://api.devnet.solana.com"
        client = AsyncClient(rpc_url)
        
        try:
            # Query a known devnet account (system program)
            pubkey = Pubkey.from_string("11111111111111111111111111111111")
            
            response = await client.get_balance(pubkey)
            balance = response.value
            
            print(f"\n✅ Balance query successful: {balance} lamports")
            
            assert balance >= 0
            
        finally:
            await client.close()
    
    async def test_get_slot(self):
        """Test getting current slot"""
        from solana.rpc.async_api import AsyncClient
        
        rpc_url = "https://api.devnet.solana.com"
        client = AsyncClient(rpc_url)
        
        try:
            response = await client.get_slot()
            slot = response.value
            
            print(f"\n✅ Current slot: {slot}")
            
            assert slot > 0
            
        finally:
            await client.close()

@pytest.mark.asyncio
class TestWalletOperations:
    """Test wallet loading and operations"""
    
    async def test_load_wallets(self):
        """Test loading wallets from disk"""
        from modules.utils import load_wallets
        
        wallets = load_wallets()
        
        print(f"\n✅ Loaded {len(wallets)} wallets from disk")
        
        assert len(wallets) > 0, "No wallets found - run wallet generation first"
        
        # Test wallet address extraction
        for i, wallet in enumerate(wallets[:3]):
            try:
                addr = str(wallet.pubkey())
            except:
                addr = str(wallet.public_key)
            
            print(f"   [{i+1}] {addr}")
            assert len(addr) > 32
    
    async def test_wallet_balance_check(self):
        """Test checking wallet balances on devnet"""
        from solana.rpc.async_api import AsyncClient
        from modules.utils import load_wallets
        from solders.pubkey import Pubkey
        
        wallets = load_wallets()
        if not wallets:
            pytest.skip("No wallets found")
        
        rpc_url = "https://api.devnet.solana.com"
        client = AsyncClient(rpc_url)
        
        try:
            wallet = wallets[0]
            
            try:
                pubkey_str = str(wallet.pubkey())
            except:
                pubkey_str = str(wallet.public_key)
            
            pubkey = Pubkey.from_string(pubkey_str)
            
            response = await client.get_balance(pubkey)
            balance = response.value / 1e9  # Convert to SOL
            
            print(f"\n✅ Main wallet balance: {balance:.4f} SOL")
            
            if balance < 0.01:
                print(f"   ⚠️ Low balance - consider airdrop")
            
            assert balance >= 0
            
        finally:
            await client.close()
    
    async def test_multiple_wallet_balances(self):
        """Test checking all wallet balances"""
        from solana.rpc.async_api import AsyncClient
        from modules.utils import load_wallets
        from solders.pubkey import Pubkey
        
        wallets = load_wallets()
        if not wallets:
            pytest.skip("No wallets found")
        
        rpc_url = "https://api.devnet.solana.com"
        client = AsyncClient(rpc_url)
        
        try:
            total_balance = 0
            funded_count = 0
            
            print(f"\n✅ Checking {len(wallets)} wallets:")
            
            for i, wallet in enumerate(wallets):
                try:
                    pubkey_str = str(wallet.pubkey())
                except:
                    pubkey_str = str(wallet.public_key)
                
                pubkey = Pubkey.from_string(pubkey_str)
                response = await client.get_balance(pubkey)
                balance = response.value / 1e9
                
                total_balance += balance
                if balance > 0:
                    funded_count += 1
                
                status = "✅" if balance > 0 else "⚠️"
                print(f"   [{i+1}] {status} {pubkey_str[:8]}... {balance:.4f} SOL")
            
            print(f"\n   Total: {total_balance:.4f} SOL across {funded_count}/{len(wallets)} funded wallets")
            
            assert total_balance >= 0
            
        finally:
            await client.close()

@pytest.mark.asyncio
class TestTransactionSimulation:
    """Test transaction building and simulation"""
    
    async def test_build_simple_transaction(self):
        """Test building a simple SOL transfer transaction"""
        from solana.rpc.async_api import AsyncClient
        from solders.transaction import Transaction
        from solders.system_program import transfer, TransferParams
        from solders.pubkey import Pubkey
        from modules.utils import load_wallets
        
        wallets = load_wallets()
        if not wallets:
            pytest.skip("No wallets found")
        
        rpc_url = "https://api.devnet.solana.com"
        client = AsyncClient(rpc_url)
        
        try:
            wallet = wallets[0]
            
            try:
                from_pubkey = wallet.pubkey()
            except:
                from_pubkey = wallet.public_key
            
            # Create dummy recipient
            to_pubkey = Pubkey.from_string("11111111111111111111111111111111")
            
            # Build transfer instruction (0.001 SOL)
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=from_pubkey,
                    to_pubkey=to_pubkey,
                    lamports=1000000  # 0.001 SOL
                )
            )
            
            # Get recent blockhash
            blockhash_response = await client.get_latest_blockhash()
            recent_blockhash = blockhash_response.value.blockhash
            
            # Build transaction with blockhash
            tx = Transaction([transfer_ix], from_pubkey, recent_blockhash)
            
            print(f"\n✅ Transaction built successfully")
            print(f"   From: {str(from_pubkey)[:16]}...")
            print(f"   To: {str(to_pubkey)[:16]}...")
            print(f"   Amount: 0.001 SOL")
            print(f"   Blockhash: {str(recent_blockhash)[:16]}...")
            
            # Note: NOT sending to avoid consuming devnet SOL
            print(f"   (Transaction not sent - simulation only)")
            
            assert tx is not None
            assert len(tx.instructions) == 1
            
        finally:
            await client.close()
    
    async def test_transaction_size(self):
        """Test transaction size limits"""
        from solana.rpc.async_api import AsyncClient
        from modules.utils import load_wallets
        
        wallets = load_wallets()
        if len(wallets) < 12:
            pytest.skip("Need at least 12 wallets")
        
        print(f"\n✅ Testing bundle transaction limits")
        print(f"   Wallets available: {len(wallets)}")
        print(f"   Target for bundle: 12")
        print(f"   Max Solana TX size: ~1232 bytes")
        
        # Estimate size per instruction
        # Each token swap ~ 200-300 bytes
        # 12 swaps ~ 2400-3600 bytes (needs multiple TXs or Jito bundle)
        
        assert len(wallets) >= 12, "Need 12+ wallets for optimized bundling"

@pytest.mark.asyncio
class TestModuleIntegration:
    """Test module initialization with real RPC"""
    
    async def test_bundler_initialization(self):
        """Test bundler initializes with devnet"""
        from modules.bundler import RugBundler
        
        rpc_url = "https://api.devnet.solana.com"
        bundler = RugBundler(rpc_url)
        
        print(f"\n✅ Bundler initialized")
        print(f"   Wallets: {len(bundler.wallets)}")
        print(f"   RPC: {bundler.rpc_url}")
        print(f"   Client type: {type(bundler.client).__name__}")
        
        assert len(bundler.wallets) > 0
        assert bundler.client is not None
        
        await bundler.client.close()
    
    async def test_rugger_initialization(self):
        """Test rugger initializes with devnet"""
        from modules.rugger import RugExecutor
        
        rpc_url = "https://api.devnet.solana.com"
        rugger = RugExecutor(rpc_url)
        
        print(f"\n✅ Rugger initialized")
        print(f"   Wallets: {len(rugger.wallets)}")
        print(f"   RPC: {rugger.rpc_url}")
        
        assert len(rugger.wallets) > 0
        assert rugger.client is not None
        
        await rugger.client.close()
    
    async def test_monitor_initialization(self):
        """Test monitor initializes with devnet"""
        from modules.monitor import HypeMonitor
        
        rpc_url = "https://api.devnet.solana.com"
        monitor = HypeMonitor(rpc_url)
        
        print(f"\n✅ Monitor initialized")
        print(f"   Wallets: {len(monitor.wallets)}")
        print(f"   RPC: {monitor.rpc_url}")
        
        assert len(monitor.wallets) > 0
        assert monitor.client is not None
        
        await monitor.client.close()

@pytest.mark.asyncio
class TestConfigValidation:
    """Validate config values for devnet"""
    
    async def test_devnet_rpc_configured(self):
        """Test that devnet RPC is configured"""
        from config import RPC_URL
        
        print(f"\n✅ RPC URL: {RPC_URL}")
        
        is_devnet = "devnet" in RPC_URL.lower()
        
        if is_devnet:
            print(f"   Mode: DEVNET (safe)")
        else:
            print(f"   ⚠️ Mode: MAINNET (use caution!)")
        
        # For testing, we expect devnet
        assert is_devnet, "Should be using devnet for Phase 2 testing"
    
    async def test_optimized_values(self):
        """Test that optimized config values are set"""
        from config import NUM_WALLETS, BUNDLE_SOL, JITO_TIP
        
        print(f"\n✅ Optimized config values:")
        print(f"   NUM_WALLETS: {NUM_WALLETS}")
        print(f"   BUNDLE_SOL: {BUNDLE_SOL}")
        print(f"   JITO_TIP: {JITO_TIP}")
        
        assert NUM_WALLETS == 12
        assert BUNDLE_SOL == 0.0025
        assert JITO_TIP == 0.0005

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

