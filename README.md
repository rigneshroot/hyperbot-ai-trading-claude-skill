# Hyperbot: Your Modular AI Trading Bot, Portable Skill, and first-class AI Plugin

Welcome to Hyperbot. 

This is a personal, modular quantitative trading bot designed for the Hyperliquid exchange (Testnet safe-by-default), authored by **Rignesh P**. 

This codebase was built to be 100% portable. It can be used in three distinct ways:
1.  **As a standard Python project:** Run backtests, sizing models, and execution loops locally in your terminal.
2.  **As a portable AI Skill:** Load the repository directly into any AI Coding Assistant (like Claude Code) and use natural language to command it (e.g., "Run a 30-day backtest on BTC").
3.  **As a standardized first-class AI Plugin:** Fully structured to be loaded directly into any AI platform supporting custom plugin registries.

---

## What makes this bot special?

Instead of relying on a single indicators setting, Hyperbot aggregates predictions across 5 self-contained trading strategies:

1.  **EMA Trend Pullback:** Follows the macro trend (EMA200) and waits for price to pull back to the fast EMA20 before entering.
2.  **RSI Mean Reversion:** Acts as a counter-trend engine, spotting extreme oversold/overbought conditions near the EMA50.
3.  **Bollinger Band Squeeze:** Capitalizes on low-volatility coiling consolidation, triggering when volume expands and breakouts occur.
4.  **Fair Value Gap (SMC):** Uses advanced Smart Money Concepts to spot price imbalances with strict closing-price fill gates.
5.  **MACD Momentum:** Rides short-term trend waves using MACD crossovers and histogram accelerations.

### The Double-Lock Security Design:
*   **The Consensus Aggregator:** Trades are only submitted if a majority of strategies (e.g., 4 out of 5) agree, and the average score in the winning direction is dominant.
*   **The Claude LLM Meta-Filter:** When a mechanical setup triggers, the bot sends the entire technical context to Claude 3.5 Sonnet to perform a quick risk audit. Claude acts as a gatekeeper—it has a unilateral veto to reject trades if it spots conflicting market conditions.

---

## How to use this project as a first-class AI Plugin

This repository includes a standardized `plugin.json` in the root and a custom skill manual under `skills/ai-trading-skill/SKILL.md`. This allows any platform supporting AI plugins to load it as a native, first-class capability extension.

### Plugin Anatomy:
*   `plugin.json`: Standard metadata configuration defining the plugin schema, naming, version, and the loadable `ai-trading-skill`.
*   `skills/ai-trading-skill/SKILL.md`: The official instructions manual that tells the host platform's agents exactly how to invoke your bot's scripts.

To load this as a plugin in your host system, point your AI registry loader to this directory. The registry will register the `ai-trading-skill` and equip its subagents with the capability to run quantitative analysis, backtesting, and automated trades on your behalf.

---

## How to use this project as a portable AI Skill

If you are using a standard AI workspace assistant without a formal plugin registry, you can still command the bot using simple, everyday natural language prompts:

*   **For Live Analysis:** 
    > "Check the live market right now for BTC and show me the strategy scores table."
    *(The AI will run `python3 analyze.py` and format the ASCII table directly in your chat).*
*   **For Simulations:** 
    > "Run a 60-day historical backtest on SOL and tell me which compounding position sizing model performed best."
    *(The AI will run the backtester, calculate returns using `pnl_calc.py`, and analyze the outputs for you).*
*   **For Development:** 
    > "Can you update the RSI strategy config to make the oversold threshold 25 instead of 30, and then re-run the unit tests to make sure everything passes?"
    *(The AI will modify `config.yaml`, run `python3 -m unittest tests/test_strategies.py`, and report back).*
*   **For Loops:** 
    > "Let's do a single execution dry-tick to make sure our exchange connections and LLM filters are working perfectly."
    *(The AI will run `python3 main.py` in one-shot mode and verify your setup).*

---

## Repository Map

Here is how the project files are laid out:

```
hyperbot/
 ├── strategies/
 │    ├── base.py          # Indicators calculations and StrategySignal structure
 │    ├── ema_trend.py     # Strategy 1: EMA Pullback
 │    ├── rsi_meanrev.py   # Strategy 2: RSI Mean Reversion
 │    ├── bb_squeeze.py    # Strategy 3: Bollinger Squeeze
 │    ├── fvg.py           # Strategy 4: Fair Value Gap (SMC)
 │    └── macd_momentum.py # Strategy 5: MACD Crossovers
 ├── aggregator.py         # The voting consensus logic
 ├── exchange_client.py    # Interacts with Hyperliquid (testnet safe-by-default)
 └── llm_filter.py         # Interfaces signal audits with Claude
 ├── tests/
 │    └── test_strategies.py # Automated testing suite
 ├── skills/
 │    └── ai-trading-skill/
 │         └── SKILL.md    # The loadable AI plugin skill instructions manual
 ├── backtest.py           # Walks historical data to simulate trades
 ├── pnl_calc.py           # Compounding equity models calculator
 ├── show_signals.py       # Displays the trade signals matrix
 ├── analyze.py            # Live read-only console visualizer
 ├── main.py               # Main bot execution scheduler daemon
 ├── config.yaml           # Central parameter file for all strategies
 ├── .env.example          # Template for credential keys
 ├── plugin.json           # Standard AI plugin definition schema metadata
 ├── ARCHITECTURE.md       # In-depth system flowcharts and quant math details
 ├── SKILL.md              # Portable AI Agent instruction manual (root fallback)
 └── requirements.txt      # Python dependencies
```

---

## Quick Setup (For Humans)

### 1. Prepare python environment
Make sure Python 3.11+ is installed. Run these commands in your terminal:

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all packages
pip install -r requirements.txt
```

### 2. Add your keys
Copy the template to create a secure, local secrets file:
```bash
cp .env.example .env
```
Open `.env` in a text editor and fill in your Hyperliquid wallet signing key and Anthropic API key. *Note: `.env` is fully git-ignored and will never be pushed to your GitHub.*

### 3. Run a quick check
```bash
# Run unit tests to make sure strategies math is 100% correct
python -m unittest tests/test_strategies.py

# See what the strategies think of the market right now (Read-Only)
python3 analyze.py

# Run a quick one-shot dry-run of the orchestrator loop
python3 main.py
```

---

## License & Author
*   **Author:** Rignesh P
*   **License:** This project is licensed under the custom [AI Learning and Research License](LICENSE). It is provided for general usage, primarily intended for AI learning, education, and quantitative research purposes.

---

## Disclaimer
Financial trading involves substantial risk. This software is provided as an experimental educational tool. Always run on Testnet before committing capital, and never let autonomous systems trade unmonitored.
