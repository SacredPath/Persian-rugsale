#!/usr/bin/env python3
"""
RPC Setup Helper
Guides user through setting up paid RPC providers
"""

import os
from pathlib import Path

def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  .env file not found. Creating from template...")
        example_path = Path("env.example")
        if example_path.exists():
            env_path.write_text(example_path.read_text())
            print("✅ Created .env file")
        else:
            print("❌ env.example not found")
            return False
    return True

def update_env_variable(key, value):
    """Update or add environment variable in .env file."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found")
        return False
    
    lines = env_path.read_text().splitlines()
    found = False
    new_lines = []
    
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"{key}={value}")
    
    env_path.write_text('\n'.join(new_lines) + '\n')
    print(f"✅ Updated {key} in .env")
    return True

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║              RPC PROVIDER SETUP                           ║
║              Helius & Shyft Configuration                 ║
╚═══════════════════════════════════════════════════════════╝

Why use paid RPC?
✅ Higher rate limits (5M-100K requests/day)
✅ Better reliability and uptime
✅ Faster transaction confirmation
✅ Priority support
✅ FREE TIERS AVAILABLE

Recommended: Helius (most reliable for Solana bots)
    """)
    
    if not check_env_file():
        return
    
    print("\n📋 Choose RPC Provider:")
    print("1. Helius (Recommended)")
    print("2. Shyft (Alternative)")
    print("3. Skip (use public RPC)")
    
    choice = input("\nChoice [1/2/3]: ").strip()
    
    if choice == "1":
        print("\n🔧 Setting up Helius RPC")
        print("\nSteps:")
        print("1. Go to: https://helius.dev")
        print("2. Sign up for free account")
        print("3. Create new API key")
        print("4. Copy your API key")
        
        api_key = input("\nEnter Helius API key (or 'skip'): ").strip()
        
        if api_key and api_key.lower() != 'skip':
            update_env_variable("HELIUS_API_KEY", api_key)
            print("\n✅ Helius configured!")
            print("\nYour RPC URLs:")
            print(f"   Devnet:  https://devnet.helius-rpc.com/?api-key={api_key}")
            print(f"   Mainnet: https://mainnet.helius-rpc.com/?api-key={api_key}")
        else:
            print("⚠️  Skipped Helius setup")
    
    elif choice == "2":
        print("\n🔧 Setting up Shyft RPC")
        print("\nSteps:")
        print("1. Go to: https://shyft.to")
        print("2. Sign up for free account")
        print("3. Get your API key from dashboard")
        print("4. Copy your API key")
        
        api_key = input("\nEnter Shyft API key (or 'skip'): ").strip()
        
        if api_key and api_key.lower() != 'skip':
            update_env_variable("SHYFT_API_KEY", api_key)
            print("\n✅ Shyft configured!")
            print(f"\nYour RPC URL: https://rpc.shyft.to?api_key={api_key}")
        else:
            print("⚠️  Skipped Shyft setup")
    
    else:
        print("\n⚠️  Using public RPC (rate-limited)")
        print("   Consider setting up paid RPC for production use")
    
    print("\n" + "="*60)
    print("✅ RPC Setup Complete!")
    print("="*60)
    print("\n💡 Next steps:")
    print("1. Edit .env to verify settings")
    print("2. Run: python quick_setup.py")
    print("3. Test: python test_devnet.py")

if __name__ == "__main__":
    main()

