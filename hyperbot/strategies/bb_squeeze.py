import pandas as pd
import numpy as np
from .base import BaseStrategy, StrategySignal

class BollingerBandSqueeze(BaseStrategy):
    def __init__(self, params: dict):
        super().__init__("Bollinger Band Squeeze", params)
        self.bb_period = params.get('bb_period', 20)
        self.bb_std = params.get('bb_std', 2.0)
        self.volatility_history = params.get('volatility_history', 50)
        self.volatility_percentile = params.get('volatility_percentile', 30)
        self.volume_sma_period = params.get('volume_sma_period', 20)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        if len(df) < max(self.bb_period, self.volatility_history, self.volume_sma_period) + 5:
            return StrategySignal(0, 0, "normal", "Insufficient data for Bollinger Squeeze")

        close = df['close']
        open_price = df['open']
        volume = df['volume']

        # Calculate Bollinger Bands
        upper_band, sma, lower_band, band_width = self.calculate_bollinger_bands(close, self.bb_period, self.bb_std)
        
        # Calculate Volume SMA
        vol_sma = volume.rolling(window=self.volume_sma_period).mean()

        # Get latest values
        curr_close = close.iloc[-1]
        curr_open = open_price.iloc[-1]
        curr_upper = upper_band.iloc[-1]
        curr_lower = lower_band.iloc[-1]
        curr_width = band_width.iloc[-1]
        curr_volume = volume.iloc[-1]
        curr_vol_sma = vol_sma.iloc[-1]

        # Calculate squeeze percentile
        width_history = band_width.iloc[-self.volatility_history:]
        min_width = width_history.min()
        max_width = width_history.max()
        
        # Avoid division by zero
        if max_width == min_width:
            squeeze_rank = 0.0
        else:
            squeeze_rank = (curr_width - min_width) / (max_width - min_width) * 100.0

        # Determine regime
        is_squeeze = squeeze_rank <= self.volatility_percentile
        
        # If bands are widening and close is outside bands, it's expansion
        if curr_width > band_width.iloc[-2] and (curr_close > curr_upper or curr_close < curr_lower):
            regime = "expansion"
        elif is_squeeze:
            regime = "squeeze"
        else:
            regime = "normal"

        buy_score = 0
        sell_score = 0
        buy_reasons = []
        sell_reasons = []

        # 1. Squeeze Active: Band width is in the bottom 30% of its history
        squeeze_points = 0
        if is_squeeze:
            squeeze_points = 25
        elif squeeze_rank <= 50: # Mild squeeze
            squeeze_points = 12

        # 2. Breakout: Price crosses outside Bollinger Bands
        breakout_buy = curr_close > curr_upper
        breakout_sell = curr_close < curr_lower

        # 3. Volume Expansion points: Proportional bonus up to 25 pts
        vol_ratio = curr_volume / curr_vol_sma if curr_vol_sma > 0 else 1.0
        volume_points = min(25, int(vol_ratio * 12.5))

        # 4. Candle direction
        candle_buy = curr_close > curr_open
        candle_sell = curr_close < curr_open

        # ---------------- BULLISH BREAKOUT (BUY) ----------------
        if squeeze_points > 0:
            buy_score += squeeze_points
            buy_reasons.append(f"Squeeze active (rank {squeeze_rank:.1f}%) (+{squeeze_points})")
            
        if breakout_buy:
            buy_score += 25
            buy_reasons.append("Breakout above upper band (+25)")
            
        if volume_points > 0:
            buy_score += volume_points
            buy_reasons.append(f"Volume expansion ({vol_ratio:.1f}x SMA) (+{volume_points})")
            
        if candle_buy:
            buy_score += 25
            buy_reasons.append("Bullish candle body (+25)")

        # ---------------- BEARISH BREAKOUT (SELL) ----------------
        if squeeze_points > 0:
            sell_score += squeeze_points
            sell_reasons.append(f"Squeeze active (rank {squeeze_rank:.1f}%) (+{squeeze_points})")
            
        if breakout_sell:
            sell_score += 25
            sell_reasons.append("Breakout below lower band (+25)")
            
        if volume_points > 0:
            sell_score += volume_points
            sell_reasons.append(f"Volume expansion ({vol_ratio:.1f}x SMA) (+{volume_points})")
            
        if candle_sell:
            sell_score += 25
            sell_reasons.append("Bearish candle body (+25)")

        # Compile reasons
        reasons = []
        if buy_score > 0 and breakout_buy:
            reasons.append(f"Buy: {', '.join(buy_reasons)}")
        if sell_score > 0 and breakout_sell:
            reasons.append(f"Sell: {', '.join(sell_reasons)}")

        # If there's a squeeze active but no breakout, it's just coiling
        if not breakout_buy and not breakout_sell:
            reason_str = f"Regime is {regime}. Bands coiling (Squeeze Rank: {squeeze_rank:.1f}%). Awaiting breakout."
            buy_score = 0
            sell_score = 0
        else:
            reason_str = "; ".join(reasons) if reasons else "No breakout signals"

        return StrategySignal(buy_score, sell_score, regime, reason_str)
