# Hyperbot - Explainable Trading Intelligence Framework

<p align="center">
  <img src="docs/images/hero_banner.png" alt="Hyperbot - Explainable Trading Intelligence" width="100%"/>
</p>

<p align="center">
  <strong>This is not a trading bot. This is a framework that explains why a trade makes sense -- or why it doesn't.</strong>
</p>

---

## The Problem with Trading Bots

Most trading bots give you a signal: **buy** or **sell**. Then you're supposed to trust it.

No context. No reasoning. No explanation of what happens if the setup fails. Just a direction and a prayer.

That's not intelligence. That's a coin flip with extra steps.

**Hyperbot takes a different approach.** It doesn't just tell you what to do -- it shows you what the market looks like from five different analytical perspectives, explains why they agree or disagree, defines exactly what would invalidate the setup, and tells you how much risk you're actually taking.

If the answer is "don't trade," it says that too. Clearly. With reasons.

---

## What Actually Happens When You Run It

When you ask Hyperbot to analyze a market, it produces a **Trade Rationale** -- a structured, multi-layer breakdown that reads like a research note, not a signal alert.

<p align="center">
  <img src="docs/images/rationale_output.png" alt="Trade Rationale Engine Output" width="600"/>
</p>

Here's what that output contains:

| Layer | What It Tells You |
|---|---|
| **Trend Direction** | Is price above or below the 200-period moving average? Are the fast and slow EMAs aligned? |
| **Volatility Regime** | Is the market coiled tight (squeeze) or expanding? Where does current volatility sit relative to recent history? |
| **Key Structural Level** | Is there a Fair Value Gap, a dynamic support/resistance zone, or a fresh imbalance nearby? |
| **Momentum State** | Is MACD crossing? Is the histogram accelerating or stalling? |
| **Risk/Reward** | Exact stop-loss and take-profit levels based on ATR, with a calculated ratio. |
| **Position Sizing** | How much of your account this trade would risk, derived from the stop distance and your risk tolerance. |
| **Invalidity Conditions** | The specific things that would break the setup. Not vague warnings -- concrete price levels and indicator states. |

The point is not prediction. The point is **structured thinking about markets**, where every assumption is visible and every exit condition is defined in advance.

---

## The Five Analysis Layers

<p align="center">
  <img src="docs/images/analysis_layers.png" alt="Five analysis layers converging into a trade rationale" width="500"/>
</p>

Instead of relying on one indicator and hoping for the best, Hyperbot runs five independent analysis engines simultaneously. Each one looks at the market from a different angle:

**1. EMA Trend Pullback** -- Follows the macro trend using the 200-period moving average. Waits for price to pull back to the fast 20-period EMA before signaling. It's patient. It doesn't chase.

**2. RSI Mean Reversion** -- The contrarian. Watches for extreme oversold or overbought conditions near key moving averages. When everyone else is panicking, this one is paying attention.

**3. Bollinger Band Squeeze** -- Detects low-volatility compression. Markets coil before they move. This layer identifies when volatility is historically tight and watches for the expansion that follows.

**4. Fair Value Gap (SMC)** -- Uses Smart Money Concepts to find price imbalances -- gaps in the market structure where institutions left footprints. Validates fills with strict close-based confirmation, not wick noise.

**5. MACD Momentum** -- Catches the short-term waves. Tracks MACD crossovers and histogram acceleration to confirm that momentum is actually behind the move, not just price noise.

A trade setup only becomes actionable when **the majority of these layers agree** and the confidence score in the winning direction meaningfully exceeds the opposing side. The framework calls this the **Consensus Aggregator**, and it exists specifically to prevent low-conviction entries.

---

## The Risk-Awareness Layer

Generating a setup is only half the job. The other half is asking: **should you actually take this trade given your current risk state?**

Hyperbot includes a configurable risk profile system with three presets:

| Profile | Max Position | Max Daily Loss | Min R/R | Best For |
|---|---|---|---|---|
| **Conservative** | 5% | -2% | 1:2.5 | Paper trading and research |
| **Moderate** | 15% | -4% | 1:2.0 | Default analysis mode |
| **Aggressive** | 25% | -6% | 1:1.5 | Only after extensive validation |

The risk layer evaluates every proposed setup against these constraints. If you've already hit your daily loss limit, it blocks new entries. If the risk/reward ratio doesn't meet the minimum threshold, it flags the setup. If fewer than 3 out of 5 strategies agree, it rejects regardless of profile.

This isn't a suggestion system. It's a guardrail.

---

## The Claude LLM Meta-Filter

When a mechanical setup triggers -- meaning the numbers say "go" -- there's one more gate before anything happens.

The entire technical context (every strategy's score, the regime classification, the proposed entry/stop/target) gets sent to Claude for a structured risk audit. Claude doesn't generate signals. It can only do one thing: **veto**.

If it spots conflicting regimes, stale levels, or structural inconsistencies that the mechanical system missed, it rejects the trade. This is a unilateral block -- there's no override.

The output is a structured JSON verdict with an explicit reason:

```json
{
  "approve": true,
  "confidence": "high",
  "reason": "Clear high timeframe EMA alignment supported by a fresh bullish FVG and accelerating MACD momentum. No Bollinger Band expansion conflicts detected."
}
```

The bot only proceeds when both `approve: true` and `confidence: high` are returned. Anything less is a rejection.

---

## Where This Fits

This repository is part of a larger ecosystem of finance-AI research tools. Each repo handles a different layer of the analysis stack:

<p align="center">
  <img src="docs/images/ecosystem_diagram.png" alt="Ecosystem Architecture" width="550"/>
</p>

| Repository | Role |
|---|---|
| **institutional-finance-skills** | Macro-level institutional positioning, 13F analysis, sector flow intelligence |
| **ai-risk-copilot** | Portfolio risk assessment, drawdown analysis, risk tolerance profiling |
| **hyperbot (this repo)** | Technical market analysis, trade rationale generation, explainable setups |

The Institutional Context module in this repo is designed as a bridge -- it can accept sector flow signals from `institutional-finance-skills` and overlay them on technical setups. The Risk Context module mirrors the schema used by `ai-risk-copilot`, so both systems can share a consistent risk language.

These aren't just three repos on a GitHub profile. They're designed to compose into a coherent research platform for understanding how markets work across multiple layers.

---

## Using This as an AI Skill

This repository is structured to work as a native skill for AI coding assistants. When loaded into Claude Code, Gemini, or any assistant that supports skill definitions, it teaches the AI how to:

- Run live market analysis: `python3 analyze.py --symbol BTC --risk-profile conservative`
- Execute historical backtests: `python3 backtest.py --days 60`
- Evaluate position sizing models: `python3 pnl_calc.py`
- Run the full orchestrator loop: `python3 main.py`

The skill definition lives at `skills/ai-trading-skill/SKILL.md` and `SKILL.md` (root). No extra configuration needed -- just load the repo and start asking questions in natural language.

### As a Claude Code Skill
When you run `claude` inside this repo, it automatically reads the skill instructions from `.claude/skills/ai-trading-skill/SKILL.md`.

### As an AI Plugin
The `plugin.json` in the root defines this as a loadable plugin for any platform supporting custom plugin registries.

---

## Repository Map

```
hyperbot-ai-trading-claude-skill/
  hyperbot/
    strategies/
      base.py                # Indicator math and StrategySignal data model
      ema_trend.py           # Layer 1: EMA Trend Pullback
      rsi_meanrev.py         # Layer 2: RSI Mean Reversion
      bb_squeeze.py          # Layer 3: Bollinger Band Squeeze
      fvg.py                 # Layer 4: Fair Value Gap (SMC)
      macd_momentum.py       # Layer 5: MACD Momentum
    aggregator.py            # Consensus voting engine
    rationale_engine.py      # Trade Rationale Engine (explainability core)
    risk_context.py          # Risk-awareness layer with profile presets
    institutional_context.py # Institutional context bridge
    exchange_client.py       # Hyperliquid API client (testnet default)
    llm_filter.py            # Claude LLM meta-filter
  tests/
    test_strategies.py       # Automated test suite
  skills/
    ai-trading-skill/
      SKILL.md               # AI agent instruction manual
  docs/
    images/                  # Documentation images
  analyze.py                 # Live market analysis with rationale output
  backtest.py                # Walk-forward historical backtester
  pnl_calc.py                # Compounding equity models calculator
  show_signals.py            # Trade signals matrix display
  main.py                    # Execution orchestrator with safety gates
  config.yaml                # All strategy parameters and settings
  plugin.json                # AI plugin definition
  ARCHITECTURE.md            # Technical system architecture
  SKILL.md                   # Root-level AI skill definition
```

---

## Quick Setup

### 1. Create your environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your keys
```bash
cp .env.example .env
```
Open `.env` and add your Hyperliquid wallet signing key and Anthropic API key. This file is git-ignored and will never be pushed.

### 3. Verify everything works
```bash
# Run the test suite
python3 -m unittest tests/test_strategies.py

# Analyze BTC with the conservative risk profile
python3 analyze.py --risk-profile conservative

# Run a 30-day backtest
python3 backtest.py --days 30
```

---

## License and Author

**Author:** Rignesh P

**License:** This project is licensed under the [AI Learning and Research License](LICENSE). It is provided for general usage, primarily intended for AI learning, education, and quantitative research purposes.

---

## A Note on Risk

Financial trading involves substantial risk. This framework is an educational and research tool designed to make trading analysis more transparent and explainable. It is not financial advice.

Always run on Testnet before committing capital. Always define your invalidation conditions before entering a trade. Always know exactly how much you're risking.

The goal of this project is not to make trading easy. It's to make trading thinking visible.
