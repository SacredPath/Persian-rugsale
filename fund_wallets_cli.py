#!/usr/bin/env python3
"""
CLI-Based Wallet Funding Script
Uses Solana CLI to batch fund wallets from main wallet
Leaves 0.02 SOL buffer in main wallet for future transactions
"""

import json
import time
import subprocess
from pathlib import Path
from decimal import Decimal

class CLIWalletFunder:
    def __init__(self, wallet_dir="wallets", buffer_sol=0.02):
        self.wallet_dir = Path(wallet_dir)
        self.buffer_sol = Decimal(str(buffer_sol))
        
    def check_solana_cli(self):
        """Check if Solana CLI is installed."""
        try:
            result = subprocess.run("solana --version", shell=True, 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Solana CLI: {result.stdout.strip()}")
                return True
            else:
                print("❌ Solana CLI not found")
                return False
        except Exception as e:
            print(f"❌ Solana CLI check failed: {e}")
            return False
    
    def get_wallet_balance(self, wallet_path):
        """Get balance using Solana CLI."""
        try:
            cmd = f"solana balance --keypair {wallet_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, 
                                  text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse balance (format: "X.XXXXXXXXX SOL")
                balance_str = result.stdout.strip().split()[0]
                return Decimal(balance_str)
            else:
                print(f"⚠️  Failed to get balance for {wallet_path}: {result.stderr}")
                return Decimal('0')
        except Exception as e:
            print(f"❌ Error getting balance: {e}")
            return Decimal('0')
    
    def transfer_sol(self, from_wallet_path, to_pubkey, amount, url="https://api.devnet.solana.com"):
        """Transfer SOL using Solana CLI with retry logic."""
        max_retries = 5
        retry_delay = 1.0
        
        for attempt in range(1, max_retries + 1):
            try:
                cmd = f"solana transfer --from {from_wallet_path} {to_pubkey} {amount} --url {url} --allow-unfunded-recipient"
                
                print(f"   Attempt {attempt}/{max_retries}: Transferring {amount} SOL to {to_pubkey[:8]}...")
                
                result = subprocess.run(cmd, shell=True, capture_output=True, 
                                      text=True, timeout=30)
                
                if result.returncode == 0:
                    # Extract signature
                    output = result.stdout.strip()
                    if "Signature:" in output:
                        sig = output.split("Signature:")[1].strip().split()[0]
                        print(f"   ✅ Success! Signature: {sig[:16]}...")
                    else:
                        print(f"   ✅ Transfer successful!")
                    return True
                else:
                    print(f"   ⚠️  Transfer failed: {result.stderr.strip()}")
                    if attempt < max_retries:
                        print(f"   Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # Exponential backoff
                    
            except subprocess.TimeoutExpired:
                print(f"   ⚠️  Transfer timed out")
                if attempt < max_retries:
                    print(f"   Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
            except Exception as e:
                print(f"   ❌ Error: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
        
        print(f"   ❌ Failed after {max_retries} attempts")
        return False
    
    def get_burner_wallets(self):
        """Get all burner wallet addresses."""
        burner_wallets = []
        for wallet_file in sorted(self.wallet_dir.glob("burner_*.json")):
            with open(wallet_file, 'r') as f:
                data = json.load(f)
                burner_wallets.append({
                    "name": wallet_file.stem,
                    "pubkey": data['publicKey'],
                    "path": str(wallet_file)
                })
        return burner_wallets
    
    def batch_fund(self, amount_per_wallet=0.001, url="https://api.devnet.solana.com"):
        """Fund all burner wallets from main wallet."""
        
        # Check Solana CLI
        if not self.check_solana_cli():
            print("\n❌ Solana CLI required. Install from:")
            print("   https://docs.solana.com/cli/install-solana-cli-tools")
            return
        
        # Check main wallet exists
        main_wallet_path = self.wallet_dir / "main_wallet.json"
        if not main_wallet_path.exists():
            print(f"❌ Main wallet not found at {main_wallet_path}")
            print("   Run: python wallet_generator.py --main")
            return
        
        # Get burner wallets
        burner_wallets = self.get_burner_wallets()
        if not burner_wallets:
            print("❌ No burner wallets found")
            print("   Run: python wallet_generator.py --count 10")
            return
        
        print(f"\n💰 Batch Funding {len(burner_wallets)} Wallets")
        print(f"   Amount per wallet: {amount_per_wallet} SOL")
        print(f"   Buffer reserved: {self.buffer_sol} SOL")
        print(f"   RPC: {url}\n")
        
        # Check main wallet balance
        print("🔍 Checking main wallet balance...")
        main_balance = self.get_wallet_balance(str(main_wallet_path))
        print(f"   Main wallet balance: {main_balance} SOL")
        
        # Calculate total needed
        total_needed = Decimal(str(amount_per_wallet)) * len(burner_wallets) + self.buffer_sol
        print(f"   Total needed: {total_needed} SOL ({amount_per_wallet} × {len(burner_wallets)} + {self.buffer_sol} buffer)")
        
        if main_balance < total_needed:
            print(f"\n❌ Insufficient balance in main wallet!")
            print(f"   Need: {total_needed} SOL")
            print(f"   Have: {main_balance} SOL")
            print(f"   Shortfall: {total_needed - main_balance} SOL")
            print(f"\n💡 Fund main wallet with:")
            print(f"   solana airdrop {float(total_needed - main_balance + Decimal('0.01'))} {self.get_main_pubkey()} --url {url}")
            return
        
        print(f"✅ Sufficient balance. Proceeding with batch funding...\n")
        
        # Fund each burner wallet
        success_count = 0
        failed_wallets = []
        
        for i, wallet in enumerate(burner_wallets, 1):
            print(f"[{i}/{len(burner_wallets)}] Funding {wallet['name']}...")
            
            if self.transfer_sol(str(main_wallet_path), wallet['pubkey'], 
                               amount_per_wallet, url):
                success_count += 1
                time.sleep(0.5)  # Small delay between transfers
            else:
                failed_wallets.append(wallet['name'])
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📊 FUNDING SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Successful: {success_count}/{len(burner_wallets)}")
        print(f"❌ Failed: {len(failed_wallets)}/{len(burner_wallets)}")
        
        if failed_wallets:
            print(f"\n⚠️  Failed wallets:")
            for name in failed_wallets:
                print(f"   - {name}")
        
        # Check final balance
        final_balance = self.get_wallet_balance(str(main_wallet_path))
        print(f"\n💰 Main wallet final balance: {final_balance} SOL")
        print(f"   (Buffer remaining: {final_balance} SOL)")
        
        if success_count == len(burner_wallets):
            print("\n✅ All wallets funded successfully!")
        elif success_count > 0:
            print(f"\n⚠️  Partially completed. {len(failed_wallets)} wallets failed.")
            print("   Re-run this script to retry failed wallets.")
        else:
            print("\n❌ Funding failed. Check errors above.")
    
    def get_main_pubkey(self):
        """Get main wallet public key."""
        main_wallet_path = self.wallet_dir / "main_wallet.json"
        if main_wallet_path.exists():
            with open(main_wallet_path, 'r') as f:
                data = json.load(f)
                return data['publicKey']
        return "MAIN_WALLET_NOT_FOUND"

def main():
    """CLI for batch funding."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch Fund Wallets using Solana CLI')
    parser.add_argument('--amount', type=float, default=0.001, 
                       help='Amount of SOL per wallet (default: 0.001)')
    parser.add_argument('--buffer', type=float, default=0.02, 
                       help='SOL buffer to keep in main wallet (default: 0.02)')
    parser.add_argument('--url', type=str, default='https://api.devnet.solana.com',
                       help='RPC URL (default: devnet)')
    parser.add_argument('--mainnet', action='store_true',
                       help='Use mainnet (CAUTION: Real SOL!)')
    
    args = parser.parse_args()
    
    # Set RPC URL
    if args.mainnet:
        url = "https://api.mainnet-beta.solana.com"
        print("\n⚠️  WARNING: MAINNET MODE - REAL SOL WILL BE SPENT!")
        response = input("   Are you SURE? Type 'YES' to continue: ")
        if response != "YES":
            print("Aborted.")
            return
    else:
        url = args.url
    
    funder = CLIWalletFunder(buffer_sol=args.buffer)
    funder.batch_fund(amount_per_wallet=args.amount, url=url)

if __name__ == "__main__":
    main()

