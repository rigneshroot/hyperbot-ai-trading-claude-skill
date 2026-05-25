import pandas as pd
import numpy as np
from .base import BaseStrategy, StrategySignal

class FairValueGap(BaseStrategy):
    def __init__(self, params: dict):
        super().__init__("Fair Value Gap", params)
        self.lookback = params.get('lookback', 50)
        self.fresh_bars = params.get('fresh_bars', 15)
        self.proximity_atr = params.get('proximity_atr', 0.25)
        self.min_gap_atr = params.get('min_gap_atr', 0.08)
        self.ema_period = params.get('ema_period', 200)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        if len(df) < self.lookback + 5:
            return StrategySignal(0, 0, "normal", "Insufficient data for Fair Value Gap")

        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']
        
        atr = self.calculate_atr(df, 14)
        ema = self.calculate_ema(close, self.ema_period)

        curr_close = close.iloc[-1]
        curr_open = open_price.iloc[-1]
        curr_atr = atr.iloc[-1]
        curr_ema = ema.iloc[-1]

        # Scan for active (unfilled) FVGs in the lookback window
        # We look back up to `self.lookback` bars ago
        active_bullish_gaps = []
        active_bearish_gaps = []

        start_idx = len(df) - self.lookback
        for i in range(start_idx, len(df) - 1):
            if i < 2:
                continue

            bar_atr = atr.iloc[i]
            
            # --- Bullish FVG detection ---
            # Gap between low of candle i and high of candle i-2
            gap_bottom = high.iloc[i-2]
            gap_top = low.iloc[i]
            if gap_top > gap_bottom and (gap_top - gap_bottom) >= self.min_gap_atr * bar_atr:
                # Check if it was filled in bars from i+1 to latest close
                is_filled = False
                for j in range(i + 1, len(df)):
                    # Filled if subsequent close closes inside/below the gap bottom
                    if close.iloc[j] <= gap_bottom:
                        is_filled = True
                        break
                if not is_filled:
                    active_bullish_gaps.append({
                        'index': i,
                        'top': gap_top,
                        'bottom': gap_bottom,
                        'size': gap_top - gap_bottom,
                        'age': len(df) - 1 - i
                    })

            # --- Bearish FVG detection ---
            # Gap between high of candle i and low of candle i-2
            gap_top = low.iloc[i-2]
            gap_bottom = high.iloc[i]
            if gap_top > gap_bottom and (gap_top - gap_bottom) >= self.min_gap_atr * bar_atr:
                # Check if it was filled in bars from i+1 to latest close
                is_filled = False
                for j in range(i + 1, len(df)):
                    # Filled if subsequent close closes inside/above the gap top
                    if close.iloc[j] >= gap_top:
                        is_filled = True
                        break
                if not is_filled:
                    active_bearish_gaps.append({
                        'index': i,
                        'top': gap_top,
                        'bottom': gap_bottom,
                        'size': gap_top - gap_bottom,
                        'age': len(df) - 1 - i
                    })

        regime = "normal"
        buy_score = 0
        sell_score = 0
        buy_reasons = []
        sell_reasons = []

        # ---------------- EVALUATE BULLISH FVG (BUY) ----------------
        if active_bullish_gaps:
            # Focus on the freshest active gap
            freshest_gap = min(active_bullish_gaps, key=lambda x: x['age'])
            gap_top = freshest_gap['top']
            gap_bottom = freshest_gap['bottom']
            age = freshest_gap['age']
            
            regime = "fvg_bullish"

            # 1. Proximity: price within proximity ATR of the gap edge (top of gap for bullish)
            # Edge is gap_top. If price goes into the gap, it gets closer to gap_bottom.
            # We check the distance of close to the gap top.
            distance = abs(curr_close - gap_top)
            prox_limit = self.proximity_atr * curr_atr
            
            if distance <= prox_limit:
                prox_points = 35
                buy_reasons.append(f"Price within FVG proximity ({distance:.2f} <= {prox_limit:.2f}) (+35)")
            else:
                # Scale down linearly past that
                # If distance is within 3x proximity ATR, scale down
                scale = max(0.0, 1.0 - (distance - prox_limit) / (2 * prox_limit))
                prox_points = int(35 * scale)
                if prox_points > 0:
                    buy_reasons.append(f"Price near FVG top (scaled proximity) (+{prox_points})")

            buy_score += prox_points

            # 2. Freshness: gap formed within last 15 bars
            if age <= self.fresh_bars:
                buy_score += 25
                buy_reasons.append(f"Fresh FVG (age {age} bars) (+25)")
            
            # 3. HTF Filter: price above EMA200
            if curr_close > curr_ema:
                buy_score += 25
                buy_reasons.append("Price > EMA200 (HTF alignment) (+25)")

            # 4. Candle confirmation
            if curr_close > curr_open:
                buy_score += 15
                buy_reasons.append("Bullish candle body (+15)")

        # ---------------- EVALUATE BEARISH FVG (SELL) ----------------
        if active_bearish_gaps:
            freshest_gap = min(active_bearish_gaps, key=lambda x: x['age'])
            gap_top = freshest_gap['top']
            gap_bottom = freshest_gap['bottom']
            age = freshest_gap['age']
            
            if regime == "normal":
                regime = "fvg_bearish"
            else:
                regime = "fvg_dual"

            # 1. Proximity: price within proximity ATR of the gap edge (bottom of gap for bearish)
            distance = abs(curr_close - gap_bottom)
            prox_limit = self.proximity_atr * curr_atr
            
            if distance <= prox_limit:
                prox_points = 35
                sell_reasons.append(f"Price within FVG proximity ({distance:.2f} <= {prox_limit:.2f}) (+35)")
            else:
                scale = max(0.0, 1.0 - (distance - prox_limit) / (2 * prox_limit))
                prox_points = int(35 * scale)
                if prox_points > 0:
                    sell_reasons.append(f"Price near FVG bottom (scaled proximity) (+{prox_points})")

            sell_score += prox_points

            # 2. Freshness: gap formed within last 15 bars
            if age <= self.fresh_bars:
                sell_score += 25
                sell_reasons.append(f"Fresh FVG (age {age} bars) (+25)")
            
            # 3. HTF Filter: price below EMA200
            if curr_close < curr_ema:
                sell_score += 25
                sell_reasons.append("Price < EMA200 (HTF alignment) (+25)")

            # 4. Candle confirmation
            if curr_close < curr_open:
                sell_score += 15
                sell_reasons.append("Bearish candle body (+15)")

        reasons = []
        if buy_score > 0:
            reasons.append(f"Buy: {', '.join(buy_reasons)}")
        if sell_score > 0:
            reasons.append(f"Sell: {', '.join(sell_reasons)}")

        reason_str = "; ".join(reasons) if reasons else "No unfilled FVG signals"

        return StrategySignal(buy_score, sell_score, regime, reason_str)
