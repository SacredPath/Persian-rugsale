# Rug Scaffold Config - FOR EDUCATIONAL TESTING ONLY
# Use .env for secrets; never commit

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# RPC Configuration - MUST be set in .env file
# Get API keys from: Helius (helius.dev) or Shyft (shyft.to)
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
SOLANA_RPC = os.getenv("SOLANA_RPC")

# Auto-configure RPC based on available keys
# Priority: SOLANA_RPC > HELIUS_API_KEY > SHYFT_API_KEY
if SOLANA_RPC:
    RPC_URL = SOLANA_RPC
    # Detect network type
    if "devnet" in SOLANA_RPC.lower():
        print("[OK] Using DEVNET (safe for testing)")
    elif "mainnet" in SOLANA_RPC.lower():
        print("[WARNING] Using MAINNET (REAL SOL - be careful!)")
    else:
        print(f"[OK] Using custom RPC: {SOLANA_RPC[:50]}...")
elif HELIUS_API_KEY:
    # Default to devnet for safety
    RPC_URL = f"https://devnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    print("[OK] Using Helius DEVNET (safe for testing)")
elif SHYFT_API_KEY:
    # Shyft automatically routes to correct network
    RPC_URL = f"https://rpc.shyft.to?api_key={SHYFT_API_KEY}&network=devnet"
    print("[OK] Using Shyft DEVNET (safe for testing)")
else:
    raise ValueError("[ERROR] RPC_URL not configured! Set HELIUS_API_KEY, SHYFT_API_KEY, or SOLANA_RPC in .env file")

# Telegram Bot Token - MUST be set in .env file
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_bot_token_here":
    raise ValueError("[ERROR] TELEGRAM_TOKEN not set! Get token from @BotFather and add to .env file or Replit Secrets")

# Program IDs and Endpoints
PUMP_FUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"  # Pump.fun
JITO_ENDPOINT = "https://ny.mainnet.block-engine.jito.wtf/api/v1/bundles"  # For bundling

# Retry Configuration
MAX_RETRIES = 5
RETRY_DELAY = 1.0  # seconds

# Rug Params (2025 OPTIMIZED for efficiency - 56% cost reduction)
NUM_WALLETS = 12  # Reduced from 20 for 40% cost savings  
BUNDLE_SOL = 0.0025  # Reduced from 0.005 for 50% savings per wallet
BUNDLE_DELAY = 3.0  # Increased to 2-4s random for organic appearance
WASH_INTERVAL = 30  # Reduced from 60s for faster monitoring response
RUG_THRESHOLD_MC = 69000  # USD MC at graduation to PumpSwap
TARGET_SUPPLY_GRAB = 0.15  # 15% supply grab (realistic)

# Volume monitoring & abort logic (prevent losses on stalled tokens)
MIN_REAL_VOLUME = 0.05  # Minimum 0.05 SOL real buys to continue monitoring
STALL_TIMEOUT = 300  # 5 minutes - auto-abort if no MC growth

# Pump.fun Fees (2025 rates)
PUMPFUN_CREATE_FEE = 0.02  # SOL - token creation fee (~$3.88)
PUMPFUN_TRADE_FEE = 0.01  # SOL - per trade fee estimate  
JITO_TIP = 0.0005  # SOL - Reduced from 0.001 for 50% tip savings

# Phase 3: Probe Mode (minimal-cost mainnet testing)
PROBE_MODE = os.getenv("PROBE_MODE", "false").lower() == "true"
if PROBE_MODE:
    print("[PROBE] Probe mode enabled - minimal spending")
    NUM_WALLETS = 2  # Only 2 wallets for probing
    BUNDLE_SOL = 0.0005  # Micro-buys (0.0005 SOL = ~$0.10)
    JITO_TIP = 0.0  # Skip tips in probe mode
    MAX_RETRIES = 2  # Fewer retries
    print(f"[PROBE] Wallets: {NUM_WALLETS}, Buy amount: {BUNDLE_SOL} SOL")
