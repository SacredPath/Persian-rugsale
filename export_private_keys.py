"""
Export private keys in Phantom-compatible format
"""
import json
import base58

def export_wallet_private_key(wallet_num):
    """Export a single wallet's private key in base58 format"""
    try:
        with open(f"wallets/wallet_{wallet_num}.json", "r") as f:
            wallet_data = json.load(f)
        
        secret_key = bytes(wallet_data["secretKey"])
        private_key_base58 = base58.b58encode(secret_key).decode('utf-8')
        
        print(f"\n{'='*60}")
        print(f"WALLET_{wallet_num}")
        print(f"{'='*60}")
        print(f"Address: {wallet_data['publicKey']}")
        print(f"Private Key (Base58): {private_key_base58}")
        print(f"{'='*60}\n")
        
        return private_key_base58
        
    except Exception as e:
        print(f"[ERROR] Failed to export wallet_{wallet_num}: {e}")
        return None

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" EXPORT PRIVATE KEYS FOR PHANTOM IMPORT")
    print("="*60)
    print("\n⚠️  WARNING: Never share these keys with anyone!")
    print("⚠️  Delete this output after importing to Phantom!\n")
    
    for i in range(4):
        export_wallet_private_key(i)
    
    print("\n" + "="*60)
    print(" HOW TO IMPORT TO PHANTOM:")
    print("="*60)
    print("1. Open Phantom wallet")
    print("2. Click Settings (gear icon)")
    print("3. Click 'Add / Connect Wallet'")
    print("4. Click 'Import Private Key'")
    print("5. Paste the Base58 private key above")
    print("6. Click 'Import'")
    print("7. Repeat for all 4 wallets")
    print("\n" + "="*60)
    print(" AFTER TRANSFERRING FUNDS:")
    print("="*60)
    print("1. Remove imported wallets from Phantom (Settings → Remove)")
    print("2. Delete this script: rm export_private_keys.py")
    print("3. Never share those private keys!")
    print("="*60 + "\n")

