"""
REAL Token Creation - Simple Implementation
Uses SPL Token standard (simplified)
"""

from solana.rpc.api import Client
try:
    from solders.transaction import Transaction
    from solders.system_program import create_account, CreateAccountParams
except ImportError:
    from solana.transaction import Transaction
    # For system program, we'll use direct instruction building
    create_account = None
    CreateAccountParams = None
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
except ImportError:
    from solana.keypair import Keypair
    from solana.publickey import PublicKey as Pubkey

def create_simple_token(creator_wallet, name, symbol, rpc_url):
    """
    **DEPRECATED - DO NOT USE IN PRODUCTION**
    
    This function only generates a random keypair WITHOUT creating a token on-chain.
    It was a fallback that caused bugs (tokens don't exist on Pump.fun/Dexscreener).
    
    Args:
        creator_wallet: Keypair of creator
        name: Token name
        symbol: Token symbol  
        rpc_url: RPC endpoint
    
    Returns:
        None (always fails in production)
    
    Note: Real token creation MUST use Pump.fun via pumpfun_real.py
    """
    print(f"[ERROR] **DEPRECATED FUNCTION CALLED: create_simple_token**")
    print(f"[ERROR] This function generates FAKE mint addresses!")
    print(f"[ERROR] Token: {name} ({symbol})")
    print(f"[ERROR] Result: NO TOKEN WILL BE CREATED ON-CHAIN")
    print(f"[ERROR] Buys/sells will FAIL because mint doesn't exist")
    print(f"[ERROR] Use Pump.fun API for real token creation")
    print(f"[ERROR] Aborting to prevent fake token creation...")
    
    return None  # Always fail to prevent fake tokens

def get_token_balance_simple(wallet_pubkey, token_mint, rpc_url):
    """
    Get REAL token balance from blockchain
    
    Args:
        wallet_pubkey: Wallet public key (string)
        token_mint: Token mint address (string)
        rpc_url: RPC endpoint
    
    Returns:
        Token balance or 0
    """
    try:
        client = Client(rpc_url)
        
        # Validate and convert pubkeys
        try:
            wallet_pk = Pubkey.from_string(wallet_pubkey)
            mint_pk = Pubkey.from_string(token_mint)
        except Exception as e:
            print(f"[ERROR] Invalid pubkey: {e}")
            return 0
        
        # Get token accounts with timeout handling
        try:
            response = client.get_token_accounts_by_owner(
                wallet_pk,
                {"mint": mint_pk}
            )
        except Exception as e:
            print(f"[ERROR] RPC call failed: {e}")
            return 0
        
        if response.value and len(response.value) > 0:
            # Parse balance from account data
            account = response.value[0]
            
            # account.account.data is base64 encoded
            # Token account structure: amount (u64) at bytes 64-72
            try:
                import base64
                import struct
                
                # Decode account data
                data = account.account.data
                if isinstance(data, str):
                    try:
                        data_bytes = base64.b64decode(data)
                    except Exception as e:
                        print(f"[ERROR] Failed to decode account data: {e}")
                        return 0
                else:
                    # Handle bytes-like objects
                    try:
                        data_bytes = bytes(data)
                    except Exception as e:
                        print(f"[ERROR] Failed to convert account data to bytes: {e}")
                        return 0
                
                # Validate data length before parsing
                if not data_bytes or len(data_bytes) < 72:
                    print(f"[WARNING] Account data too short: {len(data_bytes) if data_bytes else 0} bytes (need 72)")
                    return 0
                
                # Extract amount (u64 little-endian at offset 64)
                try:
                    amount = struct.unpack('<Q', data_bytes[64:72])[0]
                    return amount
                except struct.error as e:
                    print(f"[ERROR] Failed to unpack balance data: {e}")
                    return 0
                    
            except Exception as e:
                print(f"[WARNING] Failed to parse balance: {e}")
                return 0
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Balance check failed: {e}")
        return 0

