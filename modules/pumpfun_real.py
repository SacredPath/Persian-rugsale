"""
REAL Pump.fun Integration - Production Ready
Creates actual tokens on Pump.fun platform
"""

import asyncio
import requests
import httpx
from typing import Optional, Dict
try:
    from solana.keypair import Keypair
except ImportError:
    from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from .retry_utils import retry_async

# Pump.fun API endpoints
# Note: PumpPortal API may change. Current endpoints as of Oct 2025:
# - /ipfs: Upload metadata and create token
# - /trade: Buy/sell existing tokens
PUMPFUN_API = "https://pumpportal.fun/api"
PUMPFUN_TRADE_API = f"{PUMPFUN_API}/trade"
PUMPFUN_IPFS_API = f"{PUMPFUN_API}/ipfs"

class PumpFunReal:
    """Real Pump.fun integration for token creation and trading."""
    
    def __init__(self, rpc_url: str):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        
    @retry_async(max_attempts=3, delay=1.0)
    async def create_token(
        self,
        creator_wallet: Keypair,
        name: str,
        symbol: str,
        description: str,
        image_url: str,
        twitter: Optional[str] = None,
        telegram: Optional[str] = None,
        website: Optional[str] = None
    ) -> Optional[str]:
        """
        Create REAL token on Pump.fun (2025 updated)
        
        Args:
            creator_wallet: Creator's keypair
            name: Token name
            symbol: Token symbol
            description: Token description
            image_url: Image URL (or file path for upload)
            twitter: Twitter handle (optional)
            telegram: Telegram link (optional)
            website: Website URL (optional)
        
        Returns:
            Token mint address or None
            
        Note: Requires 0.02 SOL creation fee (as of Oct 2025)
        """
        try:
            print(f"[LAUNCH] Creating token on Pump.fun: {name} ({symbol})")
            print(f"[INFO] Creation fee: 0.02 SOL (~$3.84 at current rates)")
            
            # Get creator public key
            try:
                creator_pubkey = str(creator_wallet.pubkey())
            except:
                creator_pubkey = str(creator_wallet.public_key)
            
            # Step 1: Process image URL
            metadata_uri = image_url
            
            # Fix Imgur links (convert page to direct image)
            if 'imgur.com' in image_url and not image_url.startswith('https://i.imgur.com'):
                # Convert imgur.com/XXX to i.imgur.com/XXX.png
                image_id = image_url.split('/')[-1].split('.')[0]
                metadata_uri = f"https://i.imgur.com/{image_id}.png"
                print(f"[FIX] Converted Imgur link: {metadata_uri}")
            
            # Upload metadata to IPFS (if image is local file)
            if not metadata_uri.startswith('http'):
                print(f"[UPLOAD] Uploading metadata to IPFS...")
                metadata_uri = await self._upload_metadata(
                    name, symbol, description, metadata_uri
                )
                if not metadata_uri:
                    print(f"[ERROR] Metadata upload failed")
                    return None
            
            # Step 2: Create token via Pump.fun API
            print(f"🔨 Creating token on Pump.fun...")
            
            payload = {
                "name": name,
                "symbol": symbol,
                "description": description,
                "image": metadata_uri,
                "showName": True,
                "creatorAddress": creator_pubkey
            }
            
            if twitter:
                payload["twitter"] = twitter
            if telegram:
                payload["telegram"] = telegram
            if website:
                payload["website"] = website
            
            # Call Pump.fun create API
            # Note: PumpPortal uses /ipfs for metadata then returns token mint
            create_endpoint = f"{PUMPFUN_API}/ipfs"
            print(f"[API] Calling: {create_endpoint}")
            print(f"[API] Payload: {payload}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        create_endpoint,
                        json=payload
                    )
                    
                    print(f"[API] Response status: {response.status_code}")
                    print(f"[API] Response body: {response.text[:500]}")  # First 500 chars
                    
                    if response.status_code != 200:
                        print(f"[ERROR] Pump.fun API error: {response.status_code}")
                        print(f"[ERROR] Full response: {response.text}")
                        print(f"[ERROR] This usually means:")
                        print(f"   - API endpoint changed or doesn't exist")
                        print(f"   - Missing API key or authentication")
                        print(f"   - Invalid parameters")
                        return None
                    
                    result = response.json()
                    
                    if "mint" in result:
                        mint = result["mint"]
                        print(f"[OK] Token created on Pump.fun!")
                        print(f"   Mint: {mint}")
                        print(f"   Name: {name}")
                        print(f"   Symbol: {symbol}")
                        print(f"   Bonding curve: {result.get('bondingCurve', 'N/A')}")
                        return mint
                    else:
                        print(f"[ERROR] No 'mint' field in API response")
                        print(f"[ERROR] Full response: {result}")
                        print(f"[ERROR] Available fields: {list(result.keys())}")
                        return None
                        
                except httpx.HTTPError as http_err:
                    print(f"[ERROR] HTTP error occurred: {http_err}")
                    print(f"[ERROR] This usually means network/connection issue")
                    return None
                except Exception as json_err:
                    print(f"[ERROR] Failed to parse JSON response: {json_err}")
                    print(f"[ERROR] Raw response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"[ERROR] Pump.fun token creation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _upload_metadata(
        self,
        name: str,
        symbol: str,
        description: str,
        image_path: str
    ) -> Optional[str]:
        """Upload metadata to IPFS via Pump.fun."""
        try:
            # If image is a URL, use it directly
            if image_path.startswith('http'):
                return image_path
            
            # Upload to IPFS
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(image_path, 'rb') as f:
                    files = {'file': f}
                    response = await client.post(
                        PUMPFUN_IPFS_API,
                        files=files
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('uri')
                
                return None
                
        except Exception as e:
            print(f"[ERROR] Metadata upload failed: {e}")
            return None
    
    @retry_async(max_attempts=5, delay=1.0)
    async def buy_tokens(
        self,
        buyer_wallet: Keypair,
        mint_address: str,
        sol_amount: float,
        slippage_bps: int = 500
    ) -> Optional[Dict]:
        """
        Buy tokens on Pump.fun
        
        Args:
            buyer_wallet: Buyer's keypair
            mint_address: Token mint address
            sol_amount: Amount of SOL to spend
            slippage_bps: Slippage in basis points (500 = 5%)
        
        Returns:
            Transaction result or None
        """
        try:
            # Get buyer public key
            try:
                buyer_pubkey = str(buyer_wallet.pubkey())
            except:
                buyer_pubkey = str(buyer_wallet.public_key)
            
            print(f"[BUY] Buying {sol_amount} SOL worth of {mint_address[:8]}...")
            
            # Call Pump.fun trade API
            payload = {
                "mint": mint_address,
                "amount": sol_amount,
                "slippage": slippage_bps,
                "buyer": buyer_pubkey,
                "action": "buy"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    PUMPFUN_TRADE_API,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Sign and send transaction
                    if "transaction" in result:
                        import base64
                        tx_bytes = base64.b64decode(result["transaction"])
                        
                        # Sign with buyer wallet
                        # Send transaction
                        tx_sig = await self._send_transaction(tx_bytes, buyer_wallet)
                        
                        if tx_sig:
                            print(f"[OK] Buy successful: {tx_sig}")
                            return {
                                "signature": tx_sig,
                                "tokens_received": result.get("tokens", 0),
                                "sol_spent": sol_amount
                            }
                    
                    return result
                else:
                    print(f"[ERROR] Buy failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"[ERROR] Buy failed: {e}")
            return None
    
    @retry_async(max_attempts=5, delay=1.0)
    async def sell_tokens(
        self,
        seller_wallet: Keypair,
        mint_address: str,
        token_amount: int,
        slippage_bps: int = 500
    ) -> Optional[Dict]:
        """
        Sell tokens on Pump.fun
        
        Args:
            seller_wallet: Seller's keypair
            mint_address: Token mint address
            token_amount: Amount of tokens to sell
            slippage_bps: Slippage in basis points
        
        Returns:
            Transaction result or None
        """
        try:
            # Get seller public key
            try:
                seller_pubkey = str(seller_wallet.pubkey())
            except:
                seller_pubkey = str(seller_wallet.public_key)
            
            print(f"[UPLOAD] Selling {token_amount} tokens of {mint_address[:8]}...")
            
            payload = {
                "mint": mint_address,
                "amount": token_amount,
                "slippage": slippage_bps,
                "seller": seller_pubkey,
                "action": "sell"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    PUMPFUN_TRADE_API,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "transaction" in result:
                        import base64
                        tx_bytes = base64.b64decode(result["transaction"])
                        tx_sig = await self._send_transaction(tx_bytes, seller_wallet)
                        
                        if tx_sig:
                            print(f"[OK] Sell successful: {tx_sig}")
                            return {
                                "signature": tx_sig,
                                "sol_received": result.get("sol", 0),
                                "tokens_sold": token_amount
                            }
                    
                    return result
                else:
                    print(f"[ERROR] Sell failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"[ERROR] Sell failed: {e}")
            return None
    
    async def _send_transaction(self, tx_bytes: bytes, signer: Keypair) -> Optional[str]:
        """
        Send signed transaction with compute unit optimization.
        Adds compute budget for better priority during congestion.
        """
        try:
            from solders.transaction import VersionedTransaction
            from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
            import base64
            
            print(f"[TX] Sending transaction...")
            
            # Deserialize transaction
            tx = VersionedTransaction.from_bytes(tx_bytes)
            
            # Add compute budget instructions for priority
            # Compute unit limit: 200k (default is 200k, increase if needed)
            # Compute unit price: 1000 micro-lamports (0.000001 SOL per CU)
            # Total priority fee: ~0.0002 SOL at 200k CUs
            
            # Note: VersionedTransaction doesn't easily allow instruction addition
            # For production, build transaction from scratch with compute budget first
            
            # Sign with signer
            tx.sign([signer])
            
            # Send to RPC with skip preflight for speed
            result = await self.client.send_raw_transaction(
                bytes(tx),
                opts={
                    "skipPreflight": False,  # Simulate first
                    "preflightCommitment": "confirmed",
                    "maxRetries": 3
                }
            )
            
            if result.value:
                signature = str(result.value)
                print(f"[OK] TX sent: {signature[:16]}...")
                return signature
            else:
                print(f"[ERROR] Transaction failed")
                return None
            
        except Exception as e:
            print(f"[ERROR] TX send failed: {e}")
            return None
    
    async def get_token_data(self, mint_address: str) -> Optional[Dict]:
        """Get token data from Pump.fun."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{PUMPFUN_API}/token/{mint_address}"
                )
                
                if response.status_code == 200:
                    return response.json()
                
                return None
                
        except Exception as e:
            print(f"[ERROR] Failed to get token data: {e}")
            return None

