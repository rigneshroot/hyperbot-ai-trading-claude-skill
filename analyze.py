import argparse
import yaml
from hyperbot.exchange_client import HyperliquidClient
from hyperbot.aggregator import SignalAggregator
from hyperbot.rationale_engine import TradeRationaleEngine
from hyperbot.risk_context import RiskContextLayer
from hyperbot.institutional_context import InstitutionalContextProvider


def run_analyzer():
    parser = argparse.ArgumentParser(
        description="Explainable Trading Intelligence — Live Market Analysis"
    )
    parser.add_argument("--symbol", type=str, default=None, help="Asset to analyse (e.g. BTC)")
    parser.add_argument("--interval", type=str, default=None, help="Candle interval (e.g. 15m)")
    parser.add_argument(
        "--risk-profile",
        type=str,
        default="moderate",
        choices=["conservative", "moderate", "aggressive"],
        help="Risk tolerance profile to apply",
    )
    parser.add_argument(
        "--account-risk-pct",
        type=float,
        default=1.0,
        help="Percentage of account to risk per trade (default 1.0)",
    )
    args = parser.parse_args()

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    symbol   = args.symbol or config.get("symbol", "BTC")
    interval = args.interval or config.get("interval", "15m")
    threshold = config.get("agree_threshold", 50)
    min_agree = config.get("min_agree", 4)

    print("=" * 75)
    print("  EXPLAINABLE TRADING INTELLIGENCE FRAMEWORK")
    print(f"  Asset: {symbol}  |  Interval: {interval}  |  Risk Profile: {args.risk_profile.upper()}")
    print("=" * 75)

    # --- Fetch candles ---
    client = HyperliquidClient()
    try:
        df = client.get_candles(symbol, interval, 250)
    except Exception as e:
        print(f"Error fetching candles: {str(e)}")
        return

    # -------------------------------------------------------------------------
    # 1. Strategy scoring matrix
    # -------------------------------------------------------------------------
    aggregator = SignalAggregator(config)
    recommendation, signals, metrics = aggregator.aggregate(df)

    print(f"\n{'Strategy':<22} | {'Buy':>5} | {'Sell':>5} | {'Regime':<14} | Reason")
    print("-" * 95)

    for name, sig in signals.items():
        clean = name.replace("_", " ").title()
        b_str = f"{'*' if sig.buy_confidence >= threshold else ' '}{sig.buy_confidence}%"
        s_str = f"{'*' if sig.sell_confidence >= threshold else ' '}{sig.sell_confidence}%"
        reason = sig.reason if len(sig.reason) <= 55 else sig.reason[:52] + "..."
        print(f"{clean:<22} | {b_str:>5} | {s_str:>5} | {sig.regime:<14} | {reason}")

    print("-" * 95)
    print(f"Consensus: {recommendation.upper():<12}  "
          f"Buy: {metrics['agree_buy']}/5   Sell: {metrics['agree_sell']}/5   "
          f"Avg Buy: {metrics['avg_buy']:.1f}%   Avg Sell: {metrics['avg_sell']:.1f}%")

    # -------------------------------------------------------------------------
    # 2. Trade Rationale Engine
    # -------------------------------------------------------------------------
    engine = TradeRationaleEngine(config)
    rationale = engine.analyse(df, symbol, interval, account_risk_pct=args.account_risk_pct)
    print(rationale.display())

    # -------------------------------------------------------------------------
    # 3. Risk-Awareness Layer
    # -------------------------------------------------------------------------
    risk_layer = RiskContextLayer(profile_name=args.risk_profile, daily_pnl_pct=0.0)
    risk_assessment = risk_layer.evaluate(
        proposed_position_pct=rationale.position_sizing_pct,
        risk_reward=rationale.risk_reward,
        confidence_score=rationale.confidence_score,
        strategies_agreed=rationale.strategies_agreed,
    )
    print(risk_assessment.display())

    # -------------------------------------------------------------------------
    # 4. Institutional Context
    # -------------------------------------------------------------------------
    inst_provider = InstitutionalContextProvider()
    inst_context = inst_provider.get_context(symbol)
    print(inst_context.display())

    if recommendation in ("long", "short"):
        alignment = inst_context.alignment_note(recommendation)
        print(f"  Institutional Alignment: {alignment}")
        print()

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------
    print("=" * 75)
    print("  READ-ONLY MODE — No orders placed.")
    print("  This framework provides analysis and explainability, not predictions.")
    print("=" * 75)


if __name__ == "__main__":
    run_analyzer()
