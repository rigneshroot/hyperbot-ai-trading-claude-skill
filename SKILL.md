---
name: AI Trading Claude Skill
description: Quantitative trading, backtesting, live market analysis, and automated execution on Hyperliquid with safety risk controls and Claude LLM meta-filters.
---

# AI Trading Claude Skill

This skill equips any agent with the capability to run, backtest, analyze, audit, and manage the Hyperbot AI Trading Bot on the Hyperliquid exchange.

---

## Prerequisite Setup

Before running any script, make sure to enter the workspace, activate the virtual environment, and verify the configuration:

```bash
# 1. Enter the workspace
cd <workspace-root>

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Ensure credentials template is active
# User must configure private keys in .env for active trades.
```

---

## Operational Tasks

### 1. Run Automated Unit Tests
Verify strategy calculation consistency and technical analysis helper formulas:
```bash
python3 -m unittest tests/test_strategies.py
```
*Always ensure this returns `OK` before running simulations or active loops.*

### 2. Run Real-Time Market Analysis (Read-Only)
Analyze the live market on any supported Hyperliquid coin (default from `config.yaml`):
```bash
# Analyze default asset (BTC)
python3 analyze.py

# Analyze a custom asset on a custom interval
python3 analyze.py --symbol ETH --interval 5m
```
*This fetches live candles, runs all 5 strategies, and prints a formatted terminal ASCII table detailing the scores and consolidated recommendation.*

### 3. Run Historical Backtests
Simulate historical trades without lookahead, pagination-fetching candle data from Hyperliquid:
```bash
# Basic run (uses default 30 days)
python3 backtest.py

# Custom historical duration, strategy confidence, and consensus min agreement
python3 backtest.py --days 60 --confidence 75 --min-agree 4
```
*Outputs are saved to `backtest_results.json`.*

### 4. Evaluate Position Sizing & Compounding Returns
Evaluate PnL simulations based on backtest output logs:
```bash
python3 pnl_calc.py
```
*Calculates returns, maximum drawdowns, gross wins/losses across 4 compounding models.*

### 5. Print Signals Breakdown Matrix Table
Inspect which strategy combinations agreed on each simulated trade:
```bash
python3 show_signals.py
```

### 6. Orchestrate Execution Tick (Dry-tick / Loop Daemon)
Run the bot scheduler with safety gates, risk circuit breakers, and Claude-based LLM meta-filtering audits:
```bash
# Run one-shot dry tick (verify system connection and filter)
python3 main.py

# Daemonize active execution (runs indefinitely, polling on the timeframe interval)
python3 main.py --loop
```

---

## Customizing Strategy Settings

Agent can edit the parameters of any strategy by modifying `config.yaml` in the root of the workspace.
*   To tighten signal parameters, increase `agree_threshold` (e.g. from 50 to 75).
*   To require more unanimity, raise `min_agree` (e.g. from 3 to 4 or 5).
*   To change the traded symbol, set the `symbol` configuration (e.g. `ETH` or `SOL`).
