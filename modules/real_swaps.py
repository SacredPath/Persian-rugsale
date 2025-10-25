"""
REAL Jupiter Swaps - Simple Implementation
Actually executes transactions on blockchain
"""

import requests
import base64
from solana.rpc.api import Client
from solana.transaction import Transaction
try:
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
except ImportError:
    from solana.keypair import Keypair
    from solana.transaction import VersionedTransaction

# Token addresses
SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

def buy_token_simple(wallet, token_mint, sol_amount_lamports, rpc_url, slippage=500):
    """
    REAL buy using Jupiter - Simple version
    
    Args:
        wallet: Keypair object
        token_mint: Token to buy (mint address)
        sol_amount_lamports: Amount of SOL in lamports (1 SOL = 1e9 lamports)
        rpc_url: Solana RPC endpoint
        slippage: Slippage in bps (500 = 5%)
    
    Returns:
        Transaction signature or None
    """
    try:
        # Get wallet address
        try:
            wallet_addr = str(wallet.pubkey())
        except:
            wallet_addr = str(wallet.public_key)
        
        print(f"🔄 Buying {token_mint[:8]}... with {sol_amount_lamports / 1e9} SOL")
        
        # Step 1: Get quote from Jupiter
        quote_url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": SOL,
            "outputMint": token_mint,
            "amount": str(sol_amount_lamports),
            "slippageBps": slippage,
        }
        
        quote_response = requests.get(quote_url, params=params, timeout=10)
        quote = quote_response.json()
        
        if "error" in quote:
            print(f"[ERROR] Quote error: {quote['error']}")
            return None
        
        print(f"   Quote: {quote.get('outAmount', 0)} tokens")
        
        # Step 2: Get swap transaction
        swap_url = "https://quote-api.jup.ag/v6/swap"
        swap_payload = {
            "quoteResponse": quote,
            "userPublicKey": wallet_addr,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto"
        }
        
        swap_response = requests.post(swap_url, json=swap_payload, timeout=10)
        swap_data = swap_response.json()
        
        if "swapTransaction" not in swap_data:
            print(f"[ERROR] No swap transaction returned")
            return None
        
        # Step 3: Send transaction
        swap_tx = swap_data["swapTransaction"]
        tx_bytes = base64.b64decode(swap_tx)
        
        client = Client(rpc_url)
        tx = VersionedTransaction.from_bytes(tx_bytes)
        
        # Sign transaction
        tx.sign([wallet])
        
        # Send
        result = client.send_raw_transaction(bytes(tx), opts={"skipPreflight": False})
        sig = result.value
        
        print(f"[OK] Buy TX: {sig}")
        return sig
        
    except Exception as e:
        print(f"[ERROR] Buy failed: {e}")
        return None

def sell_token_simple(wallet, token_mint, token_amount, rpc_url, slippage=500):
    """
    REAL sell using Jupiter - Simple version
    
    Args:
        wallet: Keypair object
        token_mint: Token to sell (mint address)
        token_amount: Amount of tokens to sell (in token's smallest unit)
        rpc_url: Solana RPC endpoint
        slippage: Slippage in bps (500 = 5%)
    
    Returns:
        Transaction signature or None
    """
    try:
        # Get wallet address
        try:
            wallet_addr = str(wallet.pubkey())
        except:
            wallet_addr = str(wallet.public_key)
        
        print(f"🔄 Selling {token_amount} of {token_mint[:8]}...")
        
        # Get quote
        quote_url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": token_mint,
            "outputMint": SOL,
            "amount": str(token_amount),
            "slippageBps": slippage,
        }
        
        quote_response = requests.get(quote_url, params=params, timeout=10)
        quote = quote_response.json()
        
        if "error" in quote:
            print(f"[ERROR] Quote error: {quote['error']}")
            return None
        
        sol_out = int(quote.get('outAmount', 0)) / 1e9
        print(f"   Quote: {sol_out} SOL")
        
        # Get swap transaction
        swap_url = "https://quote-api.jup.ag/v6/swap"
        swap_payload = {
            "quoteResponse": quote,
            "userPublicKey": wallet_addr,
            "wrapAndUnwrapSol": True,
        }
        
        swap_response = requests.post(swap_url, json=swap_payload, timeout=10)
        swap_data = swap_response.json()
        
        if "swapTransaction" not in swap_data:
            print(f"[ERROR] No swap transaction returned")
            return None
        
        # Send transaction
        swap_tx = swap_data["swapTransaction"]
        tx_bytes = base64.b64decode(swap_tx)
        
        client = Client(rpc_url)
        tx = VersionedTransaction.from_bytes(tx_bytes)
        tx.sign([wallet])
        
        result = client.send_raw_transaction(bytes(tx))
        sig = result.value
        
        print(f"[OK] Sell TX: {sig}")
        return sig
        
    except Exception as e:
        print(f"[ERROR] Sell failed: {e}")
        return None

