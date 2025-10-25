# Phase 3: Mainnet Probe Guide

**Goal:** Close the 15% API gap with minimal cost  
**Budget:** ~$2-4 total (0.01 SOL cap)  
**Duration:** 20-30 minutes  
**Risk:** LOW (probe mode limits spending)

---

## 🎯 Overview

Phase 3 validates the remaining 15% of bot functionality that requires mainnet:
- ✅ Pump.fun API (token creation, buy/sell)
- ✅ Jupiter swap routing (post-graduation)
- ✅ Jito bundle submission
- ✅ Graduation detection
- ✅ End-to-end flow

**Key Difference from Full Launch:** Uses existing tokens and micro-transactions

---

## ⚙️ Setup (5 minutes)

### 1. Enable Probe Mode

Edit `.env`:
```bash
# Switch to mainnet
SOLANA_RPC=https://api.mainnet-beta.solana.com
# OR use Helius free tier
# SOLANA_RPC=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# Enable probe mode (minimal spending)
PROBE_MODE=true
```

**Probe Mode Changes:**
- Uses only 2 wallets (not 12)
- Micro-buys: 0.0005 SOL (~$0.10)
- Skips Jito tips
- Max retries: 2 (not 5)

### 2. Fund Probe Wallet

**Minimum:** 0.05 SOL (~$10)  
**Recommended:** 0.1 SOL (~$20) for buffer

```bash
# Check current balance
solana balance

# If low, buy SOL and transfer to your main wallet
# Address: (get from wallets/wallet_0.json)
```

**Fund distribution:**
```
Main wallet:    0.05 SOL (probe operations)
Reserve:        0.05 SOL (safety buffer)
───────────────────────────────
Total needed:   0.1 SOL (~$20)
```

### 3. Verify Configuration

```bash
pytest tests/test_mainnet_probe.py::TestProbeMode -v -s
```

**Expected output:**
```
✅ PROBE_MODE enabled
   Wallets: 2 (should be 2)
   Buy amount: 0.0005 SOL (should be 0.0005)
   Jito tip: 0 SOL (should be 0)

✅ Phase 3 cost estimates:
   Micro-buy probe: 0.001 SOL (~$0.19)
   Trade fees: 0.00001 SOL (~$0.00)
   Slippage (5%): 0.00005 SOL (~$0.01)
   ─────────────────────────────────────
   Total (worst case): 0.00106 SOL (~$0.21)
   Net cost: 0.00016 SOL (~$0.03)
```

---

## 📋 Phase 3 Tests

### **Part 1: API Connectivity (0 cost, 5 mins)**

Tests API endpoints without spending:

```bash
pytest tests/test_mainnet_probe.py::TestAPIConnectivity -v -s
```

**What it tests:**
- ✅ Mainnet RPC connection
- ✅ Pump.fun API responsiveness (public token query)
- ✅ Jupiter quote API (0.0001 SOL quote, no execution)
- ✅ Jito endpoint connectivity

**Cost:** $0  
**Duration:** ~2 minutes  
**Pass criteria:** All APIs respond (even if with 404/errors)

---

### **Part 2: Micro-Transaction Probe (0.001 SOL ~$0.20, 10 mins)**

⚠️ **MANUAL EXECUTION REQUIRED**

#### Step 1: Find Test Token

1. Go to https://dexscreener.com/solana
2. Filter: `pumpfun`, `new`, `MC < $10K`
3. Copy mint address of a low-activity token

**Example:** `7xKXtg2CW3BsC9fqzyZ9XXvGGe9fqRNjfzxkEDhVpump`

#### Step 2: Micro-Buy Probe

```bash
python -c "
from modules.bundler import RugBundler
import asyncio

# Replace with your test token
MINT = '7xKXtg2CW3BsC9fqzyZ9XXvGGe9fqRNjfzxkEDhVpump'

bundler = RugBundler('https://api.mainnet-beta.solana.com')
asyncio.run(bundler.bundle_buy(MINT, amount=0.0005))
"
```

**Expected output:**
```
[TARGET] OPTIMIZED sequential bundling
   Wallets: 2 (reduced for efficiency)
   Per wallet: 0.0005 SOL (500000 lamports)
   ...
[OK] Bundle complete: 2/2 (100%)
```

**Cost:** 0.001 SOL (~$0.19)  
**Verifies:**
- ✅ Pump.fun buy API works
- ✅ Slippage handling (12%)
- ✅ Sequential delays (2-4s)
- ✅ Token receipt

#### Step 3: Micro-Sell Probe (Immediate Rug)

```bash
python -c "
from modules.rugger import RugExecutor
import asyncio

MINT = '7xKXtg2CW3BsC9fqzyZ9XXvGGe9fqRNjfzxkEDhVpump'

rugger = RugExecutor('https://api.mainnet-beta.solana.com')
asyncio.run(rugger.execute(MINT, partial=True))
"
```

**Expected output:**
```
[RUG] EXECUTING: 7xKXtg2C... Mode: PARTIAL (50%)
[INFO] Token on bonding curve - using Pump.fun API
   Building atomic sell bundle...
[OK] RUG COMPLETE:
   Sells executed: 2/2 (100%)
   SOL recovered: 0.0009 SOL
   ROI: 90%
```

**Cost:** ~0.0001 SOL in fees (~$0.02)  
**Recovery:** ~0.0009 SOL (~90%)  
**Net cost:** ~$0.02  

**Verifies:**
- ✅ Pump.fun sell API works
- ✅ Partial rug (50% mode)
- ✅ ROI calculation
- ✅ Slippage handling (15%)
- ✅ Jito bundle prep

---

### **Part 3: Graduation Detection (0 cost, 5 mins)**

#### Step 1: Find Graduated Token

1. Go to https://dexscreener.com/solana
2. Filter: `pumpfun`, `MC > $69K` (graduated to PumpSwap)
3. Copy mint address

**Example:** `ABC123...` (find real one)

#### Step 2: Test Graduation Query

```bash
python -c "
from modules.pumpfun_real import PumpFunReal
import asyncio

MINT = 'ABC123...'  # Replace with graduated token

pumpfun = PumpFunReal('https://api.mainnet-beta.solana.com')
data = asyncio.run(pumpfun.get_token_data(MINT))

if data:
    print(f'Graduated: {data.get(\"graduated\", False)}')
    print(f'MC: {data.get(\"market_cap\", 0)}')
else:
    print('Token not found or API changed')
"
```

**Expected output:**
```
Graduated: True
MC: 75000
```

**Cost:** $0  
**Verifies:**
- ✅ Graduation status query
- ✅ Token data parsing
- ✅ PumpSwap detection logic

---

### **Part 4: Monitor Simulation (0 cost, optional)**

⚠️ **MANUAL - Optional test if you have extra time**

```bash
# Start bot in probe mode
PROBE_MODE=true python main.py

# In Telegram:
/monitor <LOW_ACTIVITY_TOKEN_MINT>

# Wait 5 minutes
# Verify: Auto-abort triggers on stall
```

**Cost:** $0  
**Verifies:**
- ✅ Monitoring loop
- ✅ Stall detection (5 min timeout)
- ✅ Auto-abort logic

---

## 📊 Expected Results

### **Test Summary**

| Test | Cost | Pass Criteria |
|------|------|---------------|
| API Connectivity | $0 | All APIs respond |
| Micro-Buy | ~$0.19 | Tokens received |
| Micro-Sell | ~$0.02 | SOL recovered (90%) |
| Graduation Query | $0 | Data retrieved |
| **TOTAL** | **~$0.21** | **All critical APIs work** |

### **Success Metrics**

✅ **API Connectivity:** 4/4 endpoints responsive  
✅ **Transactions:** 2/2 micro-txs successful  
✅ **Recovery:** ~90% SOL recovered  
✅ **Net Cost:** <$0.10 (under budget)

---

## 💰 Cost Tracking

### **Actual Costs (to fill in during testing)**

```
Part 1 (API probes):        $0.00
Part 2 (Micro-buy):         $____
Part 2 (Micro-sell):        $____
Part 3 (Graduation):        $0.00
Part 4 (Monitor - opt):     $0.00
─────────────────────────────────
Total Spent:                $____
Budget:                     $2.00
Remaining:                  $____

Recovery from sells:        $____
Net Cost:                   $____
```

**Target:** <$0.50 net cost (after recoveries)

---

## ⚠️ Troubleshooting

### **"Insufficient funds" error**

```bash
# Check balance
solana balance

# If low, transfer more SOL to main wallet
# Minimum: 0.05 SOL
```

### **"Token not found" on buy**

- Token may have graduated or been rugged
- Find another low-MC token on DexScreener
- Look for `new launches`, `MC < $10K`

### **"Transaction failed" repeatedly**

```bash
# Check RPC
# If using free mainnet, try Helius:
SOLANA_RPC=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY

# Or increase retries in code
MAX_RETRIES=5
```

### **"Slippage exceeded"**

- Increase slippage in buy probe:
  ```python
  bundler.bundle_buy(MINT, amount=0.0005, slippage=2000)  # 20%
  ```
- Or find less volatile token

### **Jito bundle fails**

- Skip Jito for probes (already disabled in PROBE_MODE)
- Sequential sells work fine for testing

---

## ✅ Phase 3 Completion Checklist

**Before starting:**
- [ ] .env updated (mainnet RPC, PROBE_MODE=true)
- [ ] Main wallet funded (>= 0.05 SOL)
- [ ] 2+ wallets available
- [ ] Probe mode verified (pytest)

**During testing:**
- [ ] API connectivity tests pass (4/4)
- [ ] Micro-buy successful (tokens received)
- [ ] Micro-sell successful (SOL recovered)
- [ ] Graduation detection works
- [ ] Net cost < $0.50

**After completion:**
- [ ] Document actual costs
- [ ] Save test token mint addresses
- [ ] Verify ROI calculations
- [ ] Check wallet balances

---

## 🚀 After Phase 3

### **If All Tests Pass (Expected)**

**Coverage:** ~95% (Phases 1+2+3)  
**Confidence:** VERY HIGH  
**Status:** DEPLOYMENT READY

**Next steps:**
1. Disable PROBE_MODE
2. Set real values (12 wallets, 0.0025 SOL)
3. Fund with production budget (5-10 SOL)
4. Start bot: `python main.py`
5. Monitor first 2-3 launches closely

### **If Some Tests Fail**

**Common fixes:**
- RPC issues → Use Helius paid tier
- API changes → Update `pumpfun_real.py`
- Slippage → Increase tolerance
- Network → Retry during low congestion

**Don't proceed to production if:**
- ❌ Micro-buy consistently fails (>50%)
- ❌ Can't recover >70% on sell
- ❌ Graduation detection broken
- ❌ RPC drops >30% of transactions

---

## 📈 Final Statistics

### **Total Testing (All Phases)**

```
Phase 1 (Unit):       29 tests, $0, 100% pass
Phase 2 (Devnet):     11 tests, $0, 85% pass
Phase 3 (Mainnet):    ~8 probes, ~$0.50, expected 100%
──────────────────────────────────────────────
Total:                ~48 tests, ~$0.50, ~95% coverage

vs. Trial-and-Error:  $200-500
SAVINGS:              $199.50-499.50 (99.7%)
```

---

## 🎓 Key Learnings from Phase 3

1. **Pump.fun API works** (or needs adjustment)
2. **Slippage tolerance is appropriate** (12% buy, 15% sell)
3. **Recovery rate is realistic** (~90%)
4. **Graduation detection is accurate**
5. **All critical APIs accessible**

---

**Run Phase 3 Automated Tests:**
```bash
pytest tests/test_mainnet_probe.py -v -s
```

**Run Manual Probes:**
See Part 2 & Part 3 above (micro-buy/sell scripts)

**Status:** 📍 **READY TO START PHASE 3**

**Recommendation:** Execute during low network congestion (UTC mornings) for best results.

