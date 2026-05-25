---
name: ai-trading-skill
description: Explainable trading intelligence framework. Run multi-layer market analysis, generate structured trade rationales, backtest strategies, evaluate risk profiles, and manage automated execution on Hyperliquid. Use this skill when working with Hyperbot, analyzing markets, backtesting, or generating trade rationale reports.
---

# Explainable Trading Intelligence Skill

This skill equips any agent with the ability to run market analysis, generate explainable trade rationales, backtest strategies, evaluate risk, and manage execution on the Hyperliquid exchange.

---

## Prerequisite Setup

Before running any script, activate the workspace environment:

```bash
cd <project-root>
source .venv/bin/activate
```

User must configure private keys in `.env` for active trades. See `.env.example` for required fields.

---

## Core Operations

### 1. Run Market Analysis with Trade Rationale
The primary output of this framework. Generates a structured trade rationale covering trend, volatility, momentum, key levels, sizing, and invalidity conditions.

```bash
# Default analysis (BTC, moderate risk profile)
python3 analyze.py

# Custom asset, interval, and risk profile
python3 analyze.py --symbol ETH --interval 5m --risk-profile conservative

# Adjust per-trade risk percentage
python3 analyze.py --symbol SOL --account-risk-pct 0.5
```

Available risk profiles: `conservative`, `moderate`, `aggressive`

The output includes four sections:
- Strategy scoring matrix (all 5 layers)
- Trade Rationale Engine output (structured breakdown)
- Risk Assessment (profile-adjusted sizing and warnings)
- Institutional Context (macro positioning data)

### 2. Run Automated Tests
Verify strategy calculations, rationale engine, and risk layer:
```bash
python3 -m unittest tests/test_strategies.py
```

### 3. Run Historical Backtests
Walk-forward simulation with no lookahead bias:
```bash
python3 backtest.py
python3 backtest.py --days 60 --confidence 75 --min-agree 4
```

### 4. Evaluate Position Sizing Models
Calculate compounding returns and drawdowns from backtest results:
```bash
python3 pnl_calc.py
```

### 5. View Signals Breakdown
Inspect per-trade strategy agreement matrix:
```bash
python3 show_signals.py
```

### 6. Run Execution Orchestrator
Full execution loop with safety gates, risk circuit breakers, and LLM audit:
```bash
# One-shot dry tick
python3 main.py

# Continuous polling loop
python3 main.py --loop
```

---

## Configuration

Edit `config.yaml` to adjust:
- `agree_threshold`: Minimum confidence for a strategy to count as agreeing (default: 50)
- `min_agree`: Minimum strategies required for consensus (default: 4)
- `symbol`: Asset to analyze (default: BTC)
- `interval`: Candle timeframe (default: 15m)
- Individual strategy parameters under the `strategies` section
