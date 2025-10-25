#!/usr/bin/env python3
"""
Environment Variable Validator
Checks that all required environment variables are properly configured
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def validate_env():
    """Validate environment configuration."""
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║          ENVIRONMENT VALIDATION                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check if .env file exists
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        print("\n💡 Create .env file:")
        print("   1. Copy env.example to .env")
        print("   2. Edit .env and add your credentials")
        print("\n   Windows: copy env.example .env")
        print("   Linux/Mac: cp env.example .env")
        return False
    
    print("✅ .env file found")
    
    # Load environment variables
    load_dotenv()
    
    errors = []
    warnings = []
    
    # Check RPC Configuration
    print("\n🔍 Checking RPC Configuration...")
    helius_key = os.getenv("HELIUS_API_KEY")
    shyft_key = os.getenv("SHYFT_API_KEY")
    custom_rpc = os.getenv("SOLANA_RPC")
    
    if helius_key:
        print(f"   ✅ Helius API Key: {helius_key[:10]}...{helius_key[-4:]}")
    elif shyft_key:
        print(f"   ✅ Shyft API Key: {shyft_key[:10]}...{shyft_key[-4:]}")
    elif custom_rpc:
        print(f"   ✅ Custom RPC: {custom_rpc}")
        if "devnet" not in custom_rpc.lower() and "localhost" not in custom_rpc.lower():
            warnings.append("Custom RPC appears to be mainnet - ensure this is intentional")
    else:
        errors.append("No RPC configured (need HELIUS_API_KEY, SHYFT_API_KEY, or SOLANA_RPC)")
    
    # Check Telegram Token
    print("\n🔍 Checking Telegram Configuration...")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    
    if telegram_token and telegram_token != "your_bot_token_here":
        # Basic validation of telegram token format
        if ":" in telegram_token and len(telegram_token) > 20:
            print(f"   ✅ Telegram Token: {telegram_token[:10]}...{telegram_token[-4:]}")
        else:
            errors.append("TELEGRAM_TOKEN format appears invalid (should be like: 1234567890:ABC...)")
    else:
        errors.append("TELEGRAM_TOKEN not set (get from @BotFather on Telegram)")
    
    # Check wallet directory
    print("\n🔍 Checking Wallets...")
    wallet_dir = Path("wallets")
    if wallet_dir.exists():
        wallet_count = len(list(wallet_dir.glob("*.json")))
        if wallet_count > 0:
            print(f"   ✅ Found {wallet_count} wallet(s)")
        else:
            warnings.append("No wallets found - run: python wallet_generator.py")
    else:
        warnings.append("Wallet directory not found - run: python wallet_generator.py")
    
    # Print summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    if errors:
        print("\n❌ ERRORS (must fix):")
        for error in errors:
            print(f"   • {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not errors and not warnings:
        print("\n✅ All checks passed!")
        print("\n🚀 Ready to run:")
        print("   python main.py")
        return True
    elif not errors:
        print("\n⚠️  Configuration valid but has warnings")
        print("\n🚀 You can proceed, but review warnings above")
        return True
    else:
        print("\n❌ Configuration invalid - fix errors above")
        print("\n💡 Quick setup:")
        print("   python setup_rpc.py")
        return False

def main():
    """Run validation."""
    success = validate_env()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

