import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .aggregator import SignalAggregator
from .strategies.base import BaseStrategy


@dataclass
class TradeRationale:
    """
    Structured, explainable breakdown of a trade setup.
    Emphasises reasoning and context over prediction.
    """
    symbol: str
    interval: str
    direction: str                    # 'long', 'short', or 'no_setup'
    confidence_score: int             # 0-100 composite
    strategies_agreed: int            # out of 5

    # Market state
    trend_direction: str
    volatility_regime: str
    momentum_state: str

    # Levels
    key_level_description: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float

    # Sizing
    position_sizing_pct: float
    sizing_rationale: str

    # Invalidity
    invalidity_conditions: List[str]

    # Per-strategy breakdown
    strategy_breakdown: Dict[str, dict]

    # Narrative
    summary: str

    def display(self) -> str:
        """Renders the rationale as a clean, readable console report."""
        bar = "-" * 60
        lines = [
            f"\nTrade Rationale: {self.symbol} | {self.interval} | {self.direction.upper()} Setup",
            bar,
            f"Confidence Score:      {self.confidence_score}/100  ({self.strategies_agreed}/5 strategies agree)",
            bar,
            f"Trend Direction:       {self.trend_direction}",
            f"Volatility Regime:     {self.volatility_regime}",
            f"Momentum State:        {self.momentum_state}",
            f"Key Level:             {self.key_level_description}",
            bar,
            f"Entry Price:           {self.entry_price:.4f}",
            f"Stop Loss:             {self.stop_loss:.4f}",
            f"Take Profit:           {self.take_profit:.4f}",
            f"Risk / Reward:         1:{self.risk_reward:.1f}",
            bar,
            f"Position Sizing:       {self.position_sizing_pct:.1f}% of portfolio",
            f"Sizing Rationale:      {self.sizing_rationale}",
            bar,
            "Strategy Breakdown:",
        ]

        for name, detail in self.strategy_breakdown.items():
            clean = name.replace("_", " ").title()
            agreed = "AGREE" if detail.get("agrees") else "pass"
            lines.append(f"  {clean:<22}  Buy: {detail['buy']:>3}%  Sell: {detail['sell']:>3}%  [{agreed}]")

        lines += [
            bar,
            "Invalidity Conditions (setup is void if any trigger):",
        ]
        for cond in self.invalidity_conditions:
            lines.append(f"  - {cond}")

        lines += [
            bar,
            f"Summary: {self.summary}",
            bar,
        ]
        return "\n".join(lines)


class TradeRationaleEngine:
    """
    Generates explainable trade rationale from strategy signals.

    The engine does not predict prices. It structures what the
    strategies observe, why they agree or disagree, and what
    conditions would invalidate the current setup.
    """

    def __init__(self, config: dict):
        self.config = config
        self.aggregator = SignalAggregator(config)
        self.agree_threshold = config.get("agree_threshold", 50)

    def analyse(
        self,
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        account_risk_pct: float = 1.0,
    ) -> TradeRationale:
        """
        Runs full analysis pipeline and returns a structured TradeRationale.

        Parameters
        ----------
        df              : OHLCV DataFrame (at least 220 bars)
        symbol          : Coin or ticker label
        interval        : Candle timeframe string (e.g. '15m')
        account_risk_pct: Fraction of account to risk per trade (default 1%)
        """
        recommendation, signals, metrics = self.aggregator.aggregate(df)

        curr = df.iloc[-1]
        curr_close = curr["close"]

        # --- ATR for stop sizing ---
        atr = self.aggregator.strategies["ema_trend"].calculate_atr(df, 14).iloc[-1]
        stop_distance = 1.5 * atr
        rr_ratio = 2.0

        if recommendation == "long":
            sl = curr_close - stop_distance
            tp = curr_close + stop_distance * rr_ratio
        elif recommendation == "short":
            sl = curr_close + stop_distance
            tp = curr_close - stop_distance * rr_ratio
        else:
            sl = curr_close - stop_distance
            tp = curr_close + stop_distance * rr_ratio

        # --- Position sizing via fixed fractional risk ---
        # position_size% = account_risk_pct / stop_pct
        stop_pct = (stop_distance / curr_close) * 100
        if stop_pct > 0:
            raw_size = account_risk_pct / stop_pct * 100
            position_sizing_pct = min(raw_size, 25.0)  # hard cap at 25%
        else:
            position_sizing_pct = account_risk_pct

        sizing_rationale = (
            f"Risking {account_risk_pct:.1f}% of account per trade "
            f"with a {stop_pct:.2f}% stop distance ({stop_distance:.2f} pts = 1.5 x ATR14)"
        )

        # --- Trend direction ---
        ema20 = self.aggregator.strategies["ema_trend"].calculate_ema(df["close"], 20).iloc[-1]
        ema200 = self.aggregator.strategies["ema_trend"].calculate_ema(df["close"], 200).iloc[-1]

        if curr_close > ema200 and ema20 > ema200:
            trend_direction = "Uptrend (Price > EMA200, EMA20 > EMA200)"
        elif curr_close < ema200 and ema20 < ema200:
            trend_direction = "Downtrend (Price < EMA200, EMA20 < EMA200)"
        else:
            trend_direction = "Transitioning (mixed EMA alignment)"

        # --- Volatility regime ---
        _, _, _, bw = self.aggregator.strategies["bb_squeeze"].calculate_bollinger_bands(
            df["close"], 20, 2.0
        )
        bw_history = bw.dropna().iloc[-50:]
        if len(bw_history) > 5:
            rank = (bw.iloc[-1] - bw_history.min()) / (bw_history.max() - bw_history.min() + 1e-9)
            if rank < 0.30:
                volatility_regime = f"Compressed / Squeeze (BB width at {rank*100:.0f}th percentile)"
            elif rank > 0.70:
                volatility_regime = f"Expanding / Breakout (BB width at {rank*100:.0f}th percentile)"
            else:
                volatility_regime = f"Normal range (BB width at {rank*100:.0f}th percentile)"
        else:
            volatility_regime = "Insufficient history for volatility classification"

        # --- Momentum state ---
        macd_sig = signals.get("macd_momentum")
        if macd_sig:
            if macd_sig.regime == "momentum_up":
                momentum_state = "MACD bullish crossover, histogram accelerating"
            elif macd_sig.regime == "momentum_down":
                momentum_state = "MACD bearish crossover, histogram accelerating"
            else:
                momentum_state = "MACD neutral / transitioning"
        else:
            momentum_state = "Not available"

        # --- Key level ---
        fvg_sig = signals.get("fvg")
        if fvg_sig and fvg_sig.regime not in ("normal", "error"):
            key_level_description = f"FVG detected ({fvg_sig.regime}) — {fvg_sig.reason[:80]}"
        else:
            ema_sig = signals.get("ema_trend")
            if ema_sig:
                key_level_description = f"EMA20 at {ema20:.4f} acting as dynamic support/resistance"
            else:
                key_level_description = "No significant structural level identified"

        # --- Confidence score ---
        agree_dir = "agree_buy" if recommendation == "long" else "agree_sell"
        strategies_agreed = metrics.get(agree_dir, 0)
        avg_score_key = "avg_buy" if recommendation == "long" else "avg_sell"
        confidence_score = int(min(100, metrics.get(avg_score_key, 0)))

        # --- Strategy breakdown ---
        strategy_breakdown = {}
        for name, sig in signals.items():
            buy = sig.buy_confidence
            sell = sig.sell_confidence
            agrees = (
                buy >= self.agree_threshold if recommendation == "long"
                else sell >= self.agree_threshold if recommendation == "short"
                else False
            )
            strategy_breakdown[name] = {"buy": buy, "sell": sell, "agrees": agrees}

        # --- Invalidity conditions ---
        invalidity_conditions = []

        if recommendation == "long":
            invalidity_conditions += [
                f"Close below {sl:.4f} (stop-loss breach)",
                f"Price closes back below EMA200 ({ema200:.4f}) on daily timeframe",
                "RSI drops below 40 without recovery",
                "MACD histogram turns negative",
            ]
            fvg_sig_obj = signals.get("fvg")
            if fvg_sig_obj and "fvg_bullish" in fvg_sig_obj.regime:
                invalidity_conditions.append("Bullish FVG fills on a candle close (close-based, not wick)")
        elif recommendation == "short":
            invalidity_conditions += [
                f"Close above {sl:.4f} (stop-loss breach)",
                f"Price closes back above EMA200 ({ema200:.4f}) on daily timeframe",
                "RSI recovers above 60",
                "MACD histogram turns positive",
            ]
        else:
            invalidity_conditions = ["No active setup — conditions for entry not met across strategy suite"]

        # --- Summary narrative ---
        if recommendation in ("long", "short"):
            summary = (
                f"{strategies_agreed}/5 analysis layers aligned on a {recommendation} setup. "
                f"The {trend_direction.split('(')[0].strip()} environment with "
                f"{volatility_regime.split('(')[0].strip().lower()} volatility supports the setup. "
                f"Risk is defined at {stop_pct:.2f}% of entry with a 1:{rr_ratio:.1f} reward target."
            )
        else:
            summary = (
                "Market conditions do not currently meet the multi-layer consensus threshold. "
                "Insufficient alignment across trend, momentum, and structure analysis layers. "
                "Observation mode only — no actionable setup identified."
            )

        return TradeRationale(
            symbol=symbol,
            interval=interval,
            direction=recommendation if recommendation != "stand_aside" else "no_setup",
            confidence_score=confidence_score,
            strategies_agreed=strategies_agreed,
            trend_direction=trend_direction,
            volatility_regime=volatility_regime,
            momentum_state=momentum_state,
            key_level_description=key_level_description,
            entry_price=curr_close,
            stop_loss=sl,
            take_profit=tp,
            risk_reward=rr_ratio,
            position_sizing_pct=round(position_sizing_pct, 2),
            sizing_rationale=sizing_rationale,
            invalidity_conditions=invalidity_conditions,
            strategy_breakdown=strategy_breakdown,
            summary=summary,
        )
