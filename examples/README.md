# Example Outputs

These are representative outputs from the Hyperbot Explainable Trading Intelligence Framework. Each example shows the complete pipeline output: strategy scoring, trade rationale, risk assessment, and institutional context.

The examples are chosen to demonstrate three different outcomes the framework produces:

---

## 1. [BTC Long Setup](btc_long_setup.md) -- Approved

A clean long setup where 4/5 analysis layers agree. The trade rationale walks through the trend structure, a fresh Fair Value Gap acting as support, expanding volatility, and MACD confirmation. The moderate risk profile approves the position.

**What it shows:** How the framework structures a clear, actionable setup with explicit entry, stop, target, sizing, and invalidity conditions.

---

## 2. [ETH No Setup](eth_no_setup.md) -- Stand Aside

The market is in a transitional state with mixed EMAs, flat MACD, mid-range RSI, and no structural imbalances. Zero strategies reach the agreement threshold. The framework correctly identifies this as a no-trade environment.

**What it shows:** The framework saying "there is nothing to do right now" with the same rigor it uses for actionable setups. This is arguably the most important output a trading system can produce.

---

## 3. [SOL Short -- Risk Rejected](sol_short_risk_rejected.md) -- Flagged

A technically valid short setup (4/5 agree) that gets rejected by the conservative risk profile. The position size exceeds the conservative cap, and the risk/reward ratio is below the conservative minimum.

**What it shows:** The same setup can be valid for one risk tolerance and invalid for another. The risk layer makes that distinction explicit rather than assuming one-size-fits-all.

---

## Generating Your Own

Run the analyzer against any supported Hyperliquid asset:

```bash
# BTC with moderate risk profile
python3 analyze.py --symbol BTC --risk-profile moderate

# ETH on 5-minute candles with conservative profile
python3 analyze.py --symbol ETH --interval 5m --risk-profile conservative

# SOL with aggressive profile and custom risk percentage
python3 analyze.py --symbol SOL --risk-profile aggressive --account-risk-pct 2.0
```
