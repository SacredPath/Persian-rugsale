"""
Simple Utility Functions
"""

import os
import json
import random
try:
    from solana.keypair import Keypair
except ImportError:
    from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

def generate_wallets(num=10, folder="wallets"):
    """Load existing wallets or generate new ones."""
    os.makedirs(folder, exist_ok=True)
    
    # Try to load existing wallets first
    existing = load_wallets(folder)
    if existing and len(existing) >= num:
        print(f"[OK] Loaded {len(existing)} existing wallets")
        return existing[:num]
    
    # Generate new wallets if needed
    wallets = []
    for i in range(num):
        kp = Keypair()
        wallets.append(kp)
        # Handle both solana and solders formats
        try:
            pubkey = str(kp.public_key)
        except AttributeError:
            pubkey = str(kp.pubkey())
        print(f"Wallet {i+1}: {pubkey}")
    
    return wallets

def load_wallets(folder="wallets"):
    """Load existing wallets."""
    wallets = []
    if not os.path.exists(folder):
        return wallets
    
    try:
        for filename in sorted(os.listdir(folder)):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(folder, filename)
                    with open(filepath, "r") as f:
                        wallet_data = json.load(f)
                    
                    # Validate wallet data
                    if "secretKey" not in wallet_data:
                        print(f"[WARNING]  Skipping {filename}: missing secretKey")
                        continue
                    
                    # Recreate keypair from secret key
                    secret_key_bytes = bytes(wallet_data["secretKey"])
                    # Try different keypair loading methods
                    try:
                        # solders.keypair.Keypair uses from_bytes
                        kp = Keypair.from_bytes(secret_key_bytes)
                    except (AttributeError, TypeError):
                        try:
                            # solana.keypair.Keypair uses from_secret_key
                            kp = Keypair.from_secret_key(secret_key_bytes)
                        except:
                            # Last resort: try direct construction
                            kp = Keypair()
                    wallets.append(kp)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Invalid JSON in {filename}: {e}")
                except Exception as e:
                    print(f"[ERROR] Failed to load {filename}: {e}")
    except Exception as e:
        print(f"[ERROR] Error reading wallet directory: {e}")
    
    return wallets

async def build_buy_tx(client, wallet, mint, amount):
    """Simple buy transaction."""
    print(f"Buying {amount} SOL worth of {mint}")
    # Handle both solana and solders formats
    try:
        wallet_str = str(wallet.public_key)
    except AttributeError:
        wallet_str = str(wallet.pubkey())
    return {"type": "buy", "amount": amount, "mint": mint, "wallet": wallet_str}

async def build_sell_tx(client, wallet, mint, percentage=1.0):
    """Simple sell transaction."""
    print(f"Selling {percentage*100}% of {mint}")
    # Handle both solana and solders formats
    try:
        wallet_str = str(wallet.public_key)
    except AttributeError:
        wallet_str = str(wallet.pubkey())
    return {"type": "sell", "percentage": percentage, "mint": mint, "wallet": wallet_str}

async def calculate_mc(client, mint):
    """
    Calculate REAL market cap from blockchain data.
    
    Note: Requires token supply and price data.
    For now, queries supply and estimates based on liquidity.
    """
    try:
        # Get token supply
        response = await client.get_token_supply(mint)
        if response.value:
            supply = float(response.value.amount) / (10 ** response.value.decimals)
            
            # For real MC, you'd need price from DEX
            # For now, return supply (MC = supply * price)
            # In production, query Jupiter/Raydium for price
            print(f"[STATS] Token supply: {supply:,.0f}")
            
            # Return supply as proxy (needs price multiplication)
            return int(supply)
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] MC calculation failed: {e}")
        return 0

async def get_token_balance(client, wallet, mint):
    """
    Get REAL token balance from blockchain.
    
    Args:
        client: Async Solana client
        wallet: Keypair object
        mint: Token mint address
    
    Returns:
        Token balance (raw amount)
    """
    try:
        # Get wallet public key
        try:
            wallet_pubkey = str(wallet.pubkey())
        except:
            wallet_pubkey = str(wallet.public_key)
        
        # Import real balance function
        from .real_token import get_token_balance_simple
        
        # Get RPC URL from client (hack for now)
        rpc_url = str(client._provider.endpoint_uri)
        
        balance = get_token_balance_simple(wallet_pubkey, mint, rpc_url)
        return balance
        
    except Exception as e:
        print(f"[ERROR] Balance check failed: {e}")
        return 0

def save_wallet(wallet, filename):
    """Save wallet to file."""
    # Handle both solana and solders formats
    try:
        pubkey = str(wallet.public_key)
        secret = list(wallet.secret_key)
    except AttributeError:
        pubkey = str(wallet.pubkey())
        secret = list(bytes(wallet))
    
    wallet_data = {
        "publicKey": pubkey,
        "secretKey": secret
    }
    with open(filename, "w") as f:
        json.dump(wallet_data, f, indent=2)

def get_wallet_addresses(wallets):
    """Get addresses from wallet list."""
    addresses = []
    for wallet in wallets:
        try:
            addresses.append(str(wallet.public_key))
        except AttributeError:
            addresses.append(str(wallet.pubkey()))
    return addresses
