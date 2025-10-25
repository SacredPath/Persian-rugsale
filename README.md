# Solana Rug Bot

**Educational purposes only. Rug pulls are illegal and unethical.**

## Status

- ✓ All imports working
- ✓ Pump.fun integration (real tokens)
- ✓ Jupiter swaps (real transactions)
- ✓ Windows compatible
- ✓ No placeholders

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Setup .env
cp env.example .env
# Add your HELIUS_API_KEY and TELEGRAM_TOKEN

# Run
python main.py
```

## Telegram Commands

- `/start` - Show help
- `/launch <name> <symbol> <image>` - Create token on Pump.fun
- `/monitor <mint>` - Monitor token
- `/rug <mint>` - Execute sell
- `/status` - Bot status

## Environment Variables

Required in `.env`:
```env
HELIUS_API_KEY=your_helius_key
TELEGRAM_TOKEN=your_telegram_bot_token
```

## Project Structure

```
solana-rug-scaffold/
├── main.py              # Bot entry point
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── modules/
│   ├── bundler.py       # Token creation & bundling
│   ├── rugger.py        # Sell execution
│   ├── monitor.py       # Monitoring
│   ├── pumpfun_real.py  # Pump.fun API
│   ├── real_swaps.py    # Jupiter swaps
│   ├── real_token.py    # Token utilities
│   └── utils.py         # General utilities
└── wallets/             # Generated wallets (11 wallets)
```

## Features

### Real Implementations
- **Pump.fun**: Token creation, buy/sell via API
- **Jupiter V6**: Swap fallback
- **Balance Reading**: Real blockchain queries
- **Transaction Signing**: Real private keys
- **Retry Logic**: 5x with 1s delays

### Fallbacks
- If Pump.fun fails → Jupiter swaps
- If token creation fails → Mint generation
- All errors handled gracefully

## Testing on Devnet

```bash
# Start bot
python main.py

# In Telegram
/launch TestToken TEST https://example.com/image.png
```

Bot will:
1. Create token on Pump.fun
2. Execute bundled buys
3. Monitor supply
4. Ready for `/rug` command

## Utilities

```bash
# Validate environment
python validate_env.py

# Setup RPC
python setup_rpc.py

# Fund wallets (CLI)
python fund_wallets_cli.py
```

## What Works

✓ Real Pump.fun token creation  
✓ Real buy/sell transactions  
✓ Real balance queries  
✓ Real blockchain submission  
✓ Real transaction signatures  

## Network

Currently: **DEVNET** (safe, free)  
For mainnet: Edit RPC_URL in .env (⚠️ uses real SOL)

## Support

- Check `env.example` for environment setup
- All modules have inline documentation
- Test on devnet first

## Warning

This is educational code. Rug pulls are:
- Illegal in most jurisdictions
- Unethical
- Harmful to investors

Use responsibly.
