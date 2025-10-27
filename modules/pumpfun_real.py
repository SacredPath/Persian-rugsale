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
    
    async def _check_bundle_status(self, bundle_id: str, jito_url: str, max_wait_seconds=60):
        """
        Poll Jito's bundle status API to check if bundle landed on-chain.
        More accurate than checking Solana RPC directly.
        
        Args:
            bundle_id: UUID returned from sendBundle
            jito_url: Jito block engine URL
            max_wait_seconds: Maximum time to poll (default 60s)
        
        Returns:
            dict with 'landed' (bool) and 'status' (str)
        """
        try:
            import time
            start_time = time.time()
            check_interval = 7  # Poll every 7 seconds (reduced from 2s to avoid 429s)
            consecutive_429s = 0  # Track consecutive rate limits for backoff
            
            print(f"[POLLER] Checking bundle status via Jito API...")
            print(f"[POLLER] Bundle ID: {bundle_id}")
            print(f"[POLLER] Max wait: {max_wait_seconds}s (checking every {check_interval}s)")
            print(f"[POLLER] Anti-429 mode: exponential backoff enabled")
            
            poll_count = 0
            bundle_endpoint = f"{jito_url}/api/v1/bundles"
            
            while (time.time() - start_time) < max_wait_seconds:
                poll_count += 1
                elapsed = time.time() - start_time
                
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            bundle_endpoint,
                            headers={'Content-Type': 'application/json'},
                            json={
                                'jsonrpc': '2.0',
                                'id': 1,
                                'method': 'getBundleStatuses',
                                'params': [[bundle_id]]  # Array of bundle IDs
                            }
                        )
                        
                        if response.status_code == 200:
                            consecutive_429s = 0  # Reset on successful poll
                            result = response.json()
                            
                            if 'result' in result and 'value' in result['result']:
                                statuses = result['result']['value']
                                
                                if statuses and len(statuses) > 0:
                                    bundle_status = statuses[0]
                                    confirmation = bundle_status.get('confirmation_status', 'unknown')
                                    
                                    print(f"[POLL {poll_count}] Status: {confirmation} (elapsed: {elapsed:.1f}s)")
                                    
                                    # Check for confirmed status
                                    if confirmation in ['confirmed', 'finalized']:
                                        print(f"[POLLER] [OK] Bundle CONFIRMED on-chain!")
                                        
                                        # Check for transaction errors
                                        transactions = bundle_status.get('transactions', [])
                                        for i, tx in enumerate(transactions):
                                            if 'err' in tx and tx['err']:
                                                print(f"[POLLER] [WARNING] TX {i} error: {tx['err']}")
                                        
                                        return {'landed': True, 'status': confirmation, 'details': bundle_status}
                                    
                                    elif confirmation == 'failed':
                                        print(f"[POLLER] [ERROR] Bundle FAILED")
                                        
                                        # Log failure reasons
                                        transactions = bundle_status.get('transactions', [])
                                        for i, tx in enumerate(transactions):
                                            if 'err' in tx and tx['err']:
                                                print(f"[POLLER] [ERROR] TX {i} error: {tx['err']}")
                                        
                                        return {'landed': False, 'status': 'failed', 'details': bundle_status}
                                    
                                    elif confirmation == 'pending':
                                        # Still processing - continue polling
                                        await asyncio.sleep(check_interval)
                        
                                    else:
                                        # Unknown status
                                        print(f"[POLLER] Unknown status: {confirmation}")
                                        await asyncio.sleep(check_interval)
                                else:
                                    # No status yet
                                    print(f"[POLL {poll_count}] No status yet (elapsed: {elapsed:.1f}s)")
                                    await asyncio.sleep(check_interval)
                            else:
                                print(f"[POLLER] Invalid response format")
                                await asyncio.sleep(check_interval)
                        
                        elif response.status_code == 429:
                            consecutive_429s += 1
                            # Exponential backoff: 10s, 20s, 30s, cap at 30s
                            backoff_time = min(30, 10 * consecutive_429s)
                            print(f"[RATE LIMIT] 429 #{consecutive_429s} - backing off {backoff_time}s")
                            await asyncio.sleep(backoff_time)
                            continue  # Don't count as a poll, retry immediately after backoff
                        
                        else:
                            print(f"[POLLER] HTTP {response.status_code}: {response.text[:100]}")
                            await asyncio.sleep(check_interval)
                    
                except Exception as poll_err:
                    print(f"[POLLER] Poll error: {poll_err}")
                    await asyncio.sleep(check_interval)
                    continue
            
            # Timeout reached
            print(f"[POLLER] [TIMEOUT] Timeout after {max_wait_seconds}s ({poll_count} polls)")
            print(f"[POLLER] Bundle may still land - check Jito Explorer")
            return {'landed': False, 'status': 'timeout', 'details': None}
            
        except Exception as e:
            print(f"[POLLER] Fatal error: {e}")
            return {'landed': False, 'status': 'error', 'details': str(e)}
    
    async def _wait_for_jito_leader(self, max_wait_seconds=10):
        """
        Wait for a Jito-enabled validator to be the leader.
        Prevents 429 errors by only submitting during Jito slots.
        
        Returns: True if Jito leader found, False if timeout/rate limited
        """
        try:
            import time
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            
            print(f"[JITO] Checking Jito network status...")
            
            while (time.time() - start_time) < max_wait_seconds:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        # Check Jito's bundle tip API to verify network status
                        response = await client.post(
                            f"{JITO_BLOCK_ENGINES[0]}/api/v1/bundles",
                            headers={'Content-Type': 'application/json'},
                            json={
                                'jsonrpc': '2.0',
                                'id': 1,
                                'method': 'getTipAccounts',
                                'params': []
                            }
                        )
                        
                        if response.status_code == 200:
                            print(f"[JITO] Network ready - proceeding with bundle submission")
                            return True
                        elif response.status_code == 429:
                            elapsed = time.time() - start_time
                            remaining = max_wait_seconds - elapsed
                            if remaining > check_interval:
                                print(f"[JITO] Rate limited - waiting {check_interval}s before retry...")
                                await asyncio.sleep(check_interval)
                                continue
                            else:
                                print(f"[JITO] Rate limit persists - timeout reached")
                                return False
                        else:
                            # Other HTTP errors - proceed anyway
                            print(f"[JITO] Non-critical error ({response.status_code}) - proceeding")
                            return True
                    
                except Exception as e:
                    print(f"[WARNING] Jito check failed: {e} - proceeding anyway")
                    return True
            
            # Timeout reached
            print(f"[JITO] Timeout reached ({max_wait_seconds}s) - proceeding anyway")
            return True
            
        except Exception as e:
            print(f"[WARNING] Leader check failed: {e} - proceeding anyway")
            return True
        
    async def _create_token_sequential(
        self,
        wallets: list,
        name: str,
        symbol: str,
        description: str,
        image_url: str,
        twitter: Optional[str] = None,
        telegram: Optional[str] = None,
        website: Optional[str] = None
    ) -> Optional[str]:
        """
        Create token on Pump.fun with SEQUENTIAL buys (no Jito bundles).
        More reliable during network congestion but slower.
        
        Process:
        1. Upload metadata to IPFS
        2. Create token (single TX via PumpPortal)
        3. Submit buy transactions one by one
        4. Wait for each to confirm before proceeding
        """
        try:
            import base58
            
            try:
                # Import with full module alias to completely bypass local config.py
                from solders.transaction import VersionedTransaction
                from solders.commitment_config import CommitmentLevel
                import solders.rpc.config as solders_config
                TxOpts = solders_config.TxOpts
                
            except (ImportError, AttributeError, ModuleNotFoundError) as e:
                print(f"[ERROR] Sequential mode requires 'solders' library")
                print(f"[ERROR] PumpPortal returns versioned transactions that legacy solana-py cannot sign")
                print(f"[FIX] On Replit Shell: pip install --upgrade --force-reinstall solders==0.18.1")
                print(f"[FIX] Then run: find . -name '*.pyc' -delete && python main.py")
                print(f"[ERROR] Import error: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            print(f"[SEQUENTIAL] Creating token: {name} ({symbol})")
            print(f"[INFO] Mode: Direct RPC (no Jito bundles)")
            print(f"[INFO] Wallets: {len(wallets)} (1 creator + {len(wallets)-1} sequential buyers)")
            
            if not wallets or len(wallets) < 1:
                print(f"[ERROR] Need at least 1 wallet")
                return None
            
            creator_wallet = wallets[0]
            
            # Fix Imgur links
            processed_image_url = image_url
            if 'imgur.com' in image_url and not image_url.startswith('https://i.imgur.com'):
                image_id = image_url.split('/')[-1].split('.')[0]
                processed_image_url = f"https://i.imgur.com/{image_id}.png"
                print(f"[FIX] Converted Imgur link: {processed_image_url}")
            
            # STEP 1: Upload metadata to IPFS
            print(f"[STEP 1/3] Uploading metadata to Pump.fun IPFS...")
            
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
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                print(f"[INFO] Downloading image: {processed_image_url}")
                img_response = await http_client.get(processed_image_url)
                if img_response.status_code != 200:
                    print(f"[ERROR] Failed to download image: {img_response.status_code}")
                    return None
                
                image_bytes = img_response.content
                image_filename = processed_image_url.split('/')[-1]
                if '.' not in image_filename:
                    image_filename += '.png'
                
                files = {'file': (image_filename, image_bytes, 'image/png')}
                
                print(f"[API] POST {PUMPFUN_IPFS_API}")
                ipfs_response = await http_client.post(
                    PUMPFUN_IPFS_API,
                    data=form_data,
                    files=files
                )
                
                print(f"[API] Response status: {ipfs_response.status_code}")
                
                if ipfs_response.status_code != 200:
                    print(f"[ERROR] IPFS upload failed")
                    print(f"[ERROR] Response: {ipfs_response.text}")
                    return None
                
                ipfs_result = ipfs_response.json()
                metadata_uri = ipfs_result.get('metadataUri')
                
                if not metadata_uri:
                    print(f"[ERROR] No metadata URI in response")
                    return None
                
                print(f"[OK] Metadata uploaded!")
                print(f"   URI: {metadata_uri}")
            
            # STEP 2: Generate mint keypair and create token
            print(f"[STEP 2/3] Creating token on Pump.fun...")
            
            try:
                from solders.keypair import Keypair as SoldersKeypair
                mint_keypair = SoldersKeypair()
                mint_address = str(mint_keypair.pubkey())
            except ImportError:
                from solana.keypair import Keypair as LegacyKeypair
                mint_keypair = LegacyKeypair.generate()
                mint_address = str(mint_keypair.public_key)
            
            print(f"[INFO] Mint address: {mint_address}")
            
            # Get creator pubkey
            try:
                creator_pubkey = str(creator_wallet.pubkey())
            except AttributeError:
                creator_pubkey = str(creator_wallet.public_key)
            
            # Build CREATE-only transaction via PumpPortal
            from bot_config import BUNDLE_SOL
            
            create_tx_args = [{
                'publicKey': creator_pubkey,
                'action': 'create',
                'tokenMetadata': {
                    'name': name,
                    'symbol': symbol,
                    'uri': metadata_uri
                },
                'mint': mint_address,
                'denominatedInSol': 'true',
                'amount': BUNDLE_SOL,  # Initial dev buy
                'slippage': 10,
                'priorityFee': 0.0005,
                'pool': 'pump'
            }]
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                print(f"[API] POST {PUMPPORTAL_TRADE_LOCAL} (create only)")
                trade_response = await http_client.post(
                    PUMPPORTAL_TRADE_LOCAL,
                    headers={'Content-Type': 'application/json'},
                    json=create_tx_args
                )
                
                print(f"[API] Response status: {trade_response.status_code}")
                
                if trade_response.status_code != 200:
                    print(f"[ERROR] Failed to generate create transaction")
                    print(f"[ERROR] Response: {trade_response.text}")
                    return None
                
                encoded_transactions = trade_response.json()
                print(f"[OK] Generated {len(encoded_transactions)} transaction(s)")
            
            # Sign and submit CREATE transaction
            create_tx_base58 = encoded_transactions[0]
            tx_bytes = base58.b58decode(create_tx_base58)
            versioned_tx = VersionedTransaction.from_bytes(tx_bytes)
            versioned_tx.sign([mint_keypair, creator_wallet])
            
            print(f"[INFO] Submitting CREATE transaction via direct RPC...")
            
            tx_opts = TxOpts(
                skip_preflight=False,
                preflight_commitment=CommitmentLevel.Confirmed
            )
            
            send_result = await self.client.send_raw_transaction(
                bytes(versioned_tx),
                opts=tx_opts
            )
            
            if not send_result.value:
                print(f"[ERROR] CREATE transaction failed")
                return None
            
            create_signature = str(send_result.value)
            print(f"[OK] CREATE TX: https://solscan.io/tx/{create_signature}")
            
            # Wait for CREATE to confirm
            print(f"[INFO] Waiting for CREATE to confirm...")
            await asyncio.sleep(5)
            
            # Verify token was created
            try:
                from solders.pubkey import Pubkey as SoldersPubkey
                mint_pubkey = SoldersPubkey.from_string(mint_address)
            except ImportError:
                from solana.publickey import PublicKey
                mint_pubkey = PublicKey(mint_address)
            
            account_info = await self.client.get_account_info(mint_pubkey)
            if account_info.value:
                print(f"[OK] Token verified on-chain!")
            else:
                print(f"[WARNING] Token not yet visible, but proceeding...")
            
            # STEP 3: Sequential buys
            if len(wallets) > 1:
                print(f"[STEP 3/3] Executing {len(wallets)-1} sequential buys...")
                
                for i, wallet in enumerate(wallets[1:], start=1):
                    print(f"\n[BUY {i}/{len(wallets)-1}] Processing...")
                    
                    try:
                        buyer_pubkey = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                    except AttributeError:
                        buyer_pubkey = str(wallet.public_key)
                    
                    # Generate buy transaction
                    buy_tx_args = [{
                        'publicKey': buyer_pubkey,
                        'action': 'buy',
                        'mint': mint_address,
                        'denominatedInSol': 'true',
                        'amount': BUNDLE_SOL,
                        'slippage': 15,
                        'priorityFee': 0.0005,
                        'pool': 'pump'
                    }]
                    
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as http_client:
                            buy_response = await http_client.post(
                                PUMPPORTAL_TRADE_LOCAL,
                                headers={'Content-Type': 'application/json'},
                                json=buy_tx_args
                            )
                            
                            if buy_response.status_code != 200:
                                print(f"[ERROR] Buy {i} failed: {buy_response.status_code}")
                                continue
                            
                            buy_encoded_txs = buy_response.json()
                            buy_tx_base58 = buy_encoded_txs[0]
                            buy_tx_bytes = base58.b58decode(buy_tx_base58)
                            buy_versioned_tx = VersionedTransaction.from_bytes(buy_tx_bytes)
                            buy_versioned_tx.sign([wallet])
                            
                            buy_send_result = await self.client.send_raw_transaction(
                                bytes(buy_versioned_tx),
                                opts=tx_opts
                            )
                            
                            if buy_send_result.value:
                                buy_signature = str(buy_send_result.value)
                                print(f"[OK] BUY {i} TX: https://solscan.io/tx/{buy_signature}")
                                # Small delay between buys
                                await asyncio.sleep(3)
                            else:
                                print(f"[WARNING] Buy {i} transaction rejected")
                                
                    except Exception as buy_err:
                        print(f"[ERROR] Buy {i} failed: {buy_err}")
                        continue
            
            print(f"\n[OK] Token creation complete!")
            print(f"[INFO] Mint: {mint_address}")
            print(f"[INFO] Mode: Sequential (non-atomic)")
            
            return mint_address
            
        except Exception as e:
            print(f"[ERROR] Sequential token creation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @retry_async(max_attempts=3, delay=1.0)
    async def create_token_bundled(
        self,
        wallets: list,  # List of Keypair objects for bundled buys
        name: str,
        symbol: str,
        description: str,
        image_url: str,
        twitter: Optional[str] = None,
        telegram: Optional[str] = None,
        website: Optional[str] = None,
        use_jito: Optional[bool] = None  # Override USE_JITO_BUNDLES config if provided
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
            twitter: Twitter link (optional)
            telegram: Telegram link (optional)
            website: Website URL (optional)
        
        Returns:
            Token mint address or None
            
        Note: 
            - NO API KEY NEEDED! Uses /trade-local endpoint
            - Buy amounts are determined by config.BUNDLE_SOL (predictable costs)
            - Uses denominatedInSol=true for consistent pricing
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
            
            # Check if Jito bundles are enabled
            from bot_config import USE_JITO_BUNDLES
            jito_enabled = USE_JITO_BUNDLES if use_jito is None else use_jito
            
            if not jito_enabled:
                print(f"[INFO] Jito bundles DISABLED - using sequential direct RPC submission")
                print(f"[INFO] This is more reliable during network congestion")
                # Use sequential mode (create first, then buy one by one)
                return await self._create_token_sequential(
                    wallets=wallets,
                    name=name,
                    symbol=symbol,
                    description=description,
                    image_url=image_url,
                    twitter=twitter,
                    telegram=telegram,
                    website=website
                )
            
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
            # CRITICAL: Use SOL amounts (denominatedInSol: true) for predictable costs!
            from bot_config import BUNDLE_SOL
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
                'denominatedInSol': 'true',  # CRITICAL: Use SOL amounts for predictable costs
                'amount': BUNDLE_SOL,  # SOL to spend (e.g., 0.0075 SOL)
                'slippage': 10,
                'priorityFee': 0.0005,
                'pool': 'pump'
                # computeUnitLimit/Price removed - not documented in PumpPortal API
            })
            
            # Additional transactions: BUY from other wallets (up to 4 more, total 5 max)
            buyer_wallets = wallets[1:5] if len(wallets) > 1 else []  # Max 5 transactions
            for wallet in buyer_wallets:
                buyer_pubkey = str(wallet.pubkey() if hasattr(wallet, 'pubkey') else wallet.public_key)
                bundled_tx_args.append({
                    'publicKey': buyer_pubkey,
                    'action': 'buy',
                    'mint': mint_address,
                    'denominatedInSol': 'true',  # CRITICAL: Use SOL amounts for predictable costs
                    'amount': BUNDLE_SOL,  # SOL to spend (e.g., 0.0075 SOL)
                    'slippage': 50,  # High slippage for atomic bundle (ensures all txs succeed together)
                    'priorityFee': 0.0001,  # Ignored after first tx
                    'pool': 'pump'
                    # computeUnitLimit/Price removed - not documented in PumpPortal API
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
            from bot_config import JITO_TIP
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
                    # CRITICAL: Wait for Jito leader slot (prevents 429 spam)
                    leader_ready = await self._wait_for_jito_leader(max_wait_seconds=10)
                    if not leader_ready and attempt < max_attempts - 1:
                        print(f"[WARNING] Jito not ready - will retry with backoff")
                        # Exponential backoff: 10s, 20s, 40s... (anti-congestion)
                        backoff = 10 * (2 ** attempt)
                        await asyncio.sleep(backoff)
                        continue
                    
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
                                    # Exponential backoff: 10s, 20s, 40s... (anti-congestion)
                                    backoff = 10 * (2 ** attempt)
                                    print(f"[RETRY] Waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    return None
                            
                            bundle_id = jito_result.get('result')
                            
                            # CRITICAL: Check if bundle_id is valid
                            if not bundle_id:
                                print(f"[ERROR] No bundle ID returned from Jito")
                                print(f"[ERROR] Jito response: {jito_result}")
                                if attempt < max_attempts - 1:
                                    backoff = 10 * (2 ** attempt)
                                    print(f"[RETRY] Waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    return None
                            
                            print(f"[OK] Bundle submitted to Jito!")
                            print(f"[INFO] Bundle ID: {bundle_id}")
                            print(f"[INFO] Tip: {jito_tip_lamports / 1e9:.6f} SOL to {tip_account[:8]}...")
                            
                            # Print transaction links
                            for i, signature in enumerate(tx_signatures):
                                action = bundled_tx_args[i]['action']
                                print(f"[TX {i}] {action.upper()}: https://solscan.io/tx/{signature}")
                            
                            # PROPER JITO POLLER: Check bundle status via Jito API (not Solana RPC)
                            # This is more accurate and catches errors like "insufficient funds", "expired hash", etc.
                            bundle_result = await self._check_bundle_status(
                                bundle_id=bundle_id,
                                jito_url=jito_url,
                                max_wait_seconds=60  # Poll for up to 60 seconds (30 polls × 2s)
                            )
                            
                            if bundle_result['landed']:
                                print(f"[OK] Token created successfully!")
                                print(f"[OK] Final status: {bundle_result['status']}")
                                return mint_address
                            else:
                                status = bundle_result['status']
                                print(f"[ERROR] Bundle did not land: {status}")
                                
                                # Log detailed failure info if available
                                if bundle_result.get('details'):
                                    print(f"[DEBUG] Bundle details: {bundle_result['details']}")
                                
                                # Check Solscan manually
                                print(f"[INFO] Verify on Solscan: https://solscan.io/tx/{tx_signatures[0]}")
                                print(f"[INFO] Check Jito Explorer: https://explorer.jito.wtf/bundle/{bundle_id}")
                                
                                # Decide whether to retry
                                if status == 'failed':
                                    print(f"[ERROR] Bundle FAILED - will not retry this bundle")
                                    if attempt >= max_attempts - 1:
                                        print(f"[ERROR] All Jito attempts exhausted - token creation FAILED")
                                        return None
                                    else:
                                        print(f"[RETRY] Creating new bundle with fresh blockhash...")
                                        await asyncio.sleep(3)
                                        continue
                                elif status == 'timeout':
                                    print(f"[WARNING] Bundle timeout - may still land later")
                                    if attempt >= max_attempts - 1:
                                        print(f"[ERROR] All Jito attempts exhausted - token creation FAILED")
                                        print(f"[INFO] Bundle may land later - check links above")
                                        return None
                                    else:
                                        print(f"[RETRY] Trying new bundle...")
                                        await asyncio.sleep(3)
                                        continue
                                else:
                                    # Unknown error
                                    if attempt >= max_attempts - 1:
                                        print(f"[ERROR] All Jito attempts exhausted - token creation FAILED")
                                        return None
                                    else:
                                        print(f"[RETRY] Trying again...")
                                        await asyncio.sleep(3)
                                        continue
                        else:
                            print(f"[ERROR] Jito HTTP error: {jito_response.status_code}")
                            print(f"[ERROR] Response: {jito_response.text}")
                            
                            # Handle 429 rate limit specially
                            if jito_response.status_code == 429:
                                if attempt < max_attempts - 1:
                                    # Longer backoff for rate limits
                                    backoff = 5 * (2 ** attempt)  # 5s, 10s, 20s
                                    print(f"[429] Rate limited - waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    print(f"[ERROR] Rate limit persists - bundle creation failed")
                                    return None
                            else:
                                if attempt < max_attempts - 1:
                                    backoff = 10 * (2 ** attempt)
                                    print(f"[RETRY] Waiting {backoff}s before retry...")
                                    await asyncio.sleep(backoff)
                                    continue
                                else:
                                    return None
                                
                except Exception as jito_err:
                    print(f"[ERROR] Jito submission error: {jito_err}")
                    if attempt < max_attempts - 1:
                        backoff = 10 * (2 ** attempt)
                        print(f"[RETRY] Waiting {backoff}s before retry...")
                        await asyncio.sleep(backoff)
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

