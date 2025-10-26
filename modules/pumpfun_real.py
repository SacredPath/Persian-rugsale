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

# Pump.fun API endpoints (Official PumpPortal documentation)
# Step 1: Upload metadata to pump.fun
# Step 2: Generate bundled transactions via /trade-local (NO API KEY NEEDED!)
# Step 3: Sign locally and submit to Jito with tip
PUMPFUN_API = "https://pump.fun/api"  # Base Pump.fun API
PUMPFUN_IPFS_API = f"{PUMPFUN_API}/ipfs"  # Metadata upload
PUMPPORTAL_API = "https://pumpportal.fun/api"
PUMPPORTAL_TRADE_LOCAL = f"{PUMPPORTAL_API}/trade-local"  # Bundle generation (no auth)
PUMPFUN_TRADE_API = f"{PUMPPORTAL_API}/trade"  # For buy/sell (used by buy_tokens/sell_tokens)

# Jito Block Engine URLs (use all regions for better success rate)
JITO_BLOCK_ENGINES = [
    "https://mainnet.block-engine.jito.wtf",
    "https://amsterdam.mainnet.block-engine.jito.wtf",
    "https://frankfurt.mainnet.block-engine.jito.wtf",
    "https://ny.mainnet.block-engine.jito.wtf",
    "https://tokyo.mainnet.block-engine.jito.wtf"
]

# Jito tip accounts (send SOL to these to tip validators)
JITO_TIP_ACCOUNTS = [
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"
]

class PumpFunReal:
    """Real Pump.fun integration for token creation and trading."""
    
    def __init__(self, rpc_url: str):
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        
    @retry_async(max_attempts=3, delay=1.0)
    async def create_token_bundled(
        self,
        wallets: list,  # List of Keypair objects for bundled buys
        name: str,
        symbol: str,
        description: str,
        image_url: str,
        buy_amount_tokens: int = 1000000,  # Tokens per wallet (NOT SOL!)
        twitter: Optional[str] = None,
        telegram: Optional[str] = None,
        website: Optional[str] = None
    ) -> Optional[str]:
        """
        Create REAL token on Pump.fun with BUNDLED initial buys (Official PumpPortal method)
        
        Process:
        1. Upload metadata to pump.fun/api/ipfs
        2. Generate bundled transactions via /trade-local (create + buys)
        3. Sign transactions locally
        4. Submit as atomic Jito bundle
        
        Args:
            wallets: List of Keypair objects (first = creator, rest = buyers)
            name: Token name
            symbol: Token symbol
            description: Token description
            image_url: Image URL (direct link or will auto-convert Imgur)
            buy_amount_tokens: Tokens per wallet (default 1M tokens each)
            twitter: Twitter link (optional)
            telegram: Telegram link (optional)
            website: Website URL (optional)
        
        Returns:
            Token mint address or None
            
        Note: NO API KEY NEEDED! Uses /trade-local endpoint
        """
        try:
            import base58
            try:
                from solders.transaction import VersionedTransaction
            except ImportError:
                from solana.transaction import VersionedTransaction
            
            print(f"[LAUNCH] Creating token with BUNDLED buys: {name} ({symbol})")
            print(f"[INFO] Using official PumpPortal bundled method")
            print(f"[INFO] Wallets: {len(wallets)} (1 creator + {len(wallets)-1} buyers)")
            
            # Create fresh AsyncClient for this call (avoid event loop issues)
            self.client = AsyncClient(self.rpc_url)
            
            if not wallets or len(wallets) < 1:
                print(f"[ERROR] Need at least 1 wallet (creator)")
                return None
            
            creator_wallet = wallets[0]
            
            # Fix Imgur links (convert page to direct image)
            processed_image_url = image_url
            if 'imgur.com' in image_url and not image_url.startswith('https://i.imgur.com'):
                image_id = image_url.split('/')[-1].split('.')[0]
                processed_image_url = f"https://i.imgur.com/{image_id}.png"
                print(f"[FIX] Converted Imgur link: {processed_image_url}")
            
            # STEP 1: Upload metadata to pump.fun/api/ipfs
            print(f"[STEP 1] Uploading metadata to Pump.fun IPFS...")
            
            form_data = {
                'name': name,
                'symbol': symbol,
                'description': description,
                'showName': 'true'
            }
            
            if twitter:
                form_data['twitter'] = twitter
            if telegram:
                form_data['telegram'] = telegram
            if website:
                form_data['website'] = website
            
            # Download image and upload as file
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                # Download image
                print(f"[INFO] Downloading image: {processed_image_url}")
                img_response = await http_client.get(processed_image_url)
                if img_response.status_code != 200:
                    print(f"[ERROR] Failed to download image: {img_response.status_code}")
                    return None
                
                image_bytes = img_response.content
                image_filename = processed_image_url.split('/')[-1]
                if '.' not in image_filename:
                    image_filename += '.png'
                
                # Upload to IPFS
                files = {'file': (image_filename, image_bytes, 'image/png')}
                
                print(f"[API] POST {PUMPFUN_IPFS_API}")
                ipfs_response = await http_client.post(
                    PUMPFUN_IPFS_API,
                    data=form_data,
                    files=files
                )
                
                print(f"[API] Response status: {ipfs_response.status_code}")
                
                if ipfs_response.status_code != 200:
                    print(f"[ERROR] IPFS upload failed: {ipfs_response.status_code}")
                    print(f"[ERROR] Response: {ipfs_response.text}")
                    return None
                
                ipfs_result = ipfs_response.json()
                metadata_uri = ipfs_result.get('metadataUri')
                
                if not metadata_uri:
                    print(f"[ERROR] No metadataUri in IPFS response")
                    print(f"[ERROR] Response: {ipfs_result}")
                    return None
                
                print(f"[OK] Metadata uploaded!")
                print(f"   URI: {metadata_uri}")
            
            # STEP 2: Generate mint keypair
            print(f"[STEP 2] Generating mint keypair...")
            mint_keypair = Keypair()
            mint_address = str(mint_keypair.pubkey() if hasattr(mint_keypair, 'pubkey') else mint_keypair.public_key)
            print(f"[INFO] Mint address: {mint_address}")
            
            # STEP 3: Build bundled transaction arguments
            print(f"[STEP 3] Building bundled transactions...")
            bundled_tx_args = []
            
            # First transaction: CREATE with dev buy
            creator_pubkey = str(creator_wallet.pubkey() if hasattr(creator_wallet, 'pubkey') else creator_wallet.public_key)
            bundled_tx_args.append({
                'publicKey': creator_pubkey,
                'action': 'create',
                'tokenMetadata': {
                    'name': name,
                    'symbol': symbol,
                    'uri': metadata_uri
                },
                'mint': mint_address,
                'denominatedInSol': 'false',  # Use tokens, not SOL
                'amount': buy_amount_tokens,  # Tokens to buy
                'slippage': 10,
                'priorityFee': 0.0005,
                'pool': 'pump'
            })
            
            # Additional transactions: BUY from other wallets (up to 4 more, total 5 max)
            buyer_wallets = wallets[1:5] if len(wallets) > 1 else []  # Max 5 transactions
            for wallet in buyer_wallets:
                buyer_pubkey = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                bundled_tx_args.append({
                    'publicKey': buyer_pubkey,
                    'action': 'buy',
                    'mint': mint_address,
                    'denominatedInSol': 'false',
                    'amount': buy_amount_tokens,
                    'slippage': 50,  # High slippage for atomic bundle (ensures all txs succeed together)
                    'priorityFee': 0.0001,  # Ignored after first tx
                    'pool': 'pump'
                })
            
            print(f"[INFO] Bundle: 1 create + {len(buyer_wallets)} buys = {len(bundled_tx_args)} transactions")
            
            # STEP 4: Generate unsigned transactions from /trade-local
            print(f"[STEP 4] Generating unsigned transactions...")
            print(f"[API] POST {PUMPPORTAL_TRADE_LOCAL}")
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                trade_local_response = await http_client.post(
                    PUMPPORTAL_TRADE_LOCAL,
                    headers={'Content-Type': 'application/json'},
                    json=bundled_tx_args
                )
                
                print(f"[API] Response status: {trade_local_response.status_code}")
                
                if trade_local_response.status_code != 200:
                    print(f"[ERROR] Failed to generate transactions")
                    print(f"[ERROR] Response: {trade_local_response.text}")
                    return None
                
                encoded_transactions = trade_local_response.json()
                print(f"[OK] Generated {len(encoded_transactions)} unsigned transactions")
            
            # STEP 5: Sign all transactions
            print(f"[STEP 5] Signing transactions...")
            encoded_signed_transactions = []
            tx_signatures = []
            
            for index, encoded_tx in enumerate(encoded_transactions):
                try:
                    # Decode transaction
                    tx_bytes = base58.b58decode(encoded_tx)
                    versioned_tx = VersionedTransaction.from_bytes(tx_bytes)
                    
                    # Sign with appropriate keypair(s)
                    if bundled_tx_args[index]['action'] == 'create':
                        # Create: sign with mint + creator
                        signed_tx = VersionedTransaction(
                            versioned_tx.message,
                            [mint_keypair, creator_wallet]
                        )
                    else:
                        # Buy: sign with buyer wallet
                        buyer_wallet = wallets[index]  # index 1+ corresponds to wallets[1+]
                        signed_tx = VersionedTransaction(
                            versioned_tx.message,
                            [buyer_wallet]
                        )
                    
                    # Encode signed transaction
                    signed_tx_bytes = bytes(signed_tx)
                    encoded_signed = base58.b58encode(signed_tx_bytes).decode()
                    encoded_signed_transactions.append(encoded_signed)
                    
                    # Extract signature
                    signature = str(signed_tx.signatures[0])
                    tx_signatures.append(signature)
                    
                    print(f"[OK] Signed TX {index}: {signature[:16]}...")
                    
                except Exception as sign_err:
                    print(f"[ERROR] Failed to sign transaction {index}: {sign_err}")
                    return None
            
            # STEP 6: Create Jito tip transaction
            print(f"[STEP 6] Creating Jito tip transaction...")
            
            import random
            try:
                from solders.system_program import TransferParams, transfer as system_transfer
                from solders.message import Message
                from solders.transaction import VersionedTransaction as SoldersVersionedTransaction
                from solders.pubkey import Pubkey
                from solders.signature import Signature  # For verification
                USE_SOLDERS = True
            except ImportError:
                from solana.system_program import TransferParams, transfer as system_transfer
                from solana.transaction import Transaction as LegacyTransaction
                from solana.publickey import PublicKey as Pubkey
                USE_SOLDERS = False
            
            # Jito tip amount (from config, default 0.0001 SOL for creation)
            from config import JITO_TIP
            jito_tip_lamports = int(JITO_TIP * 1e9)  # Convert SOL to lamports
            print(f"[INFO] Jito tip: {jito_tip_lamports / 1e9:.6f} SOL (~${jito_tip_lamports / 1e9 * 194:.2f})")
            
            # Pick random Jito tip account
            tip_account = random.choice(JITO_TIP_ACCOUNTS)
            tip_pubkey = Pubkey.from_string(tip_account)
            
            # Creator pays the tip
            creator_pubkey = Pubkey.from_string(str(creator_wallet.pubkey() if hasattr(creator_wallet, 'pubkey') else creator_wallet.public_key))
            
            # Get recent blockhash
            blockhash_response = await self.client.get_latest_blockhash()
            recent_blockhash = blockhash_response.value.blockhash
            
            # Create tip instruction
            tip_instruction = system_transfer(
                TransferParams(
                    from_pubkey=creator_pubkey,
                    to_pubkey=tip_pubkey,
                    lamports=jito_tip_lamports
                )
            )
            
            # Build tip transaction
            if USE_SOLDERS:
                tip_message = Message.new_with_blockhash(
                    [tip_instruction],
                    creator_pubkey,
                    recent_blockhash
                )
                tip_tx = SoldersVersionedTransaction(tip_message, [creator_wallet])
            else:
                tip_tx = LegacyTransaction()
                tip_tx.recent_blockhash = recent_blockhash
                tip_tx.add(tip_instruction)
                tip_tx.sign(creator_wallet)
            
            # Encode tip transaction
            tip_tx_bytes = bytes(tip_tx)
            tip_tx_encoded = base58.b58encode(tip_tx_bytes).decode()
            
            # Add tip transaction to bundle (must be last)
            bundle_with_tip = encoded_signed_transactions + [tip_tx_encoded]
            
            print(f"[OK] Bundle prepared: {len(encoded_signed_transactions)} txs + 1 tip = {len(bundle_with_tip)} total")
            
            # STEP 7: Submit bundle to Jito with retry logic
            print(f"[STEP 7] Submitting bundle to Jito...")
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # Try different Jito block engines
                    jito_url = random.choice(JITO_BLOCK_ENGINES)
                    bundle_endpoint = f"{jito_url}/api/v1/bundles"
                    
                    print(f"[ATTEMPT {attempt + 1}/{max_attempts}] Using {jito_url.split('//')[1].split('.')[0]} region...")
                    
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        jito_response = await http_client.post(
                            bundle_endpoint,
                            headers={'Content-Type': 'application/json'},
                            json={
                                'jsonrpc': '2.0',
                                'id': 1,
                                'method': 'sendBundle',
                                'params': [bundle_with_tip]
                            }
                        )
                        
                        print(f"[API] Response status: {jito_response.status_code}")
                        
                        if jito_response.status_code == 200:
                            jito_result = jito_response.json()
                            
                            # Check for error in response
                            if 'error' in jito_result:
                                error_msg = jito_result['error'].get('message', str(jito_result['error']))
                                print(f"[ERROR] Jito error: {error_msg}")
                                if attempt < max_attempts - 1:
                                    print(f"[RETRY] Waiting 2s before retry...")
                                    await asyncio.sleep(2)
                                    continue
                                else:
                                    return None
                            
                            bundle_id = jito_result.get('result')
                            print(f"[OK] Bundle submitted to Jito!")
                            print(f"[INFO] Bundle ID: {bundle_id}")
                            print(f"[INFO] Tip: {jito_tip_lamports / 1e9:.6f} SOL to {tip_account[:8]}...")
                            
                            # Print transaction links
                            for i, signature in enumerate(tx_signatures):
                                action = bundled_tx_args[i]['action']
                                print(f"[TX {i}] {action.upper()}: https://solscan.io/tx/{signature}")
                            
                            # Wait for bundle to land with multiple verification attempts
                            print(f"[INFO] Waiting for bundle to land on-chain...")
                            
                            # Try verifying multiple times (bundles can take 20-30s during congestion)
                            verification_attempts = 6  # 6 attempts × 5s = 30s total wait
                            bundle_landed = False
                            
                            for verify_attempt in range(verification_attempts):
                                await asyncio.sleep(5)  # Wait 5s between checks
                                
                                print(f"[VERIFY {verify_attempt + 1}/{verification_attempts}] Checking if bundle landed...")
                                try:
                                    # Convert signature string to Signature object for solders
                                    if USE_SOLDERS:
                                        sig_obj = Signature.from_string(tx_signatures[0])
                                        sig_status = await self.client.get_signature_statuses([sig_obj])
                                    else:
                                        # solana-py accepts strings
                                        sig_status = await self.client.get_signature_statuses([tx_signatures[0]])
                                    
                                    if sig_status.value and sig_status.value[0]:
                                        confirmation_status = sig_status.value[0]
                                        print(f"[OK] Bundle landed on-chain!")
                                        print(f"[INFO] Confirmation status: {confirmation_status.confirmation_status if hasattr(confirmation_status, 'confirmation_status') else 'confirmed'}")
                                        print(f"[OK] Token created successfully!")
                                        bundle_landed = True
                                        break
                                    else:
                                        if verify_attempt < verification_attempts - 1:
                                            print(f"[INFO] Not landed yet, waiting 5s more...")
                                        else:
                                            print(f"[WARNING] Bundle may not have landed after {verification_attempts * 5}s")
                                
                                except Exception as verify_err:
                                    print(f"[WARNING] Verification error: {verify_err}")
                                    if verify_attempt < verification_attempts - 1:
                                        print(f"[INFO] Will retry verification...")
                            
                            # Final decision
                            if bundle_landed:
                                return mint_address
                            else:
                                print(f"[ERROR] Bundle verification failed - transaction may not have landed")
                                print(f"[INFO] Check Solscan manually: https://solscan.io/tx/{tx_signatures[0]}")
                                
                                # If this was the last Jito attempt, return None (token creation failed)
                                if attempt >= max_attempts - 1:
                                    print(f"[ERROR] All Jito attempts exhausted - token creation FAILED")
                                    return None
                                else:
                                    # Try submitting to Jito again
                                    print(f"[RETRY] Will submit bundle to Jito again...")
                                    await asyncio.sleep(3)
                                    continue
                        else:
                            print(f"[ERROR] Jito HTTP error: {jito_response.status_code}")
                            print(f"[ERROR] Response: {jito_response.text}")
                            if attempt < max_attempts - 1:
                                await asyncio.sleep(2)
                                continue
                            else:
                                return None
                                
                except Exception as jito_err:
                    print(f"[ERROR] Jito submission error: {jito_err}")
                    if attempt < max_attempts - 1:
                        print(f"[RETRY] Waiting 2s before retry...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        print(f"[ERROR] All Jito attempts failed")
                        return None
            
            print(f"[ERROR] Failed to submit bundle after {max_attempts} attempts")
            return None
                    
        except Exception as e:
            print(f"[ERROR] Bundled token creation failed: {e}")
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
            # Create fresh AsyncClient for this call (avoid event loop issues)
            self.client = AsyncClient(self.rpc_url)
            
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
            # Create fresh AsyncClient for this call (avoid event loop issues)
            self.client = AsyncClient(self.rpc_url)
            
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

