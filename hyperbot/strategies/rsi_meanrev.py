import pandas as pd
from .base import BaseStrategy, StrategySignal

class RsiMeanReversion(BaseStrategy):
    def __init__(self, params: dict):
        super().__init__("RSI Mean Reversion", params)
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.rsi_overbought = params.get('rsi_overbought', 70)
        self.ema_period = params.get('ema_period', 50)
        self.atr_period = params.get('atr_period', 14)
        self.proximity_limit_atr = params.get('proximity_limit_atr', 1.5)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        if len(df) < max(self.ema_period, self.rsi_period, self.atr_period) + 5:
            return StrategySignal(0, 0, "ranging", "Insufficient data for RSI Mean Reversion")

        close = df['close']
        open_price = df['open']
        
        rsi = self.calculate_rsi(close, self.rsi_period)
        ema = self.calculate_ema(close, self.ema_period)
        atr = self.calculate_atr(df, self.atr_period)

        curr_close = close.iloc[-1]
        curr_open = open_price.iloc[-1]
        curr_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        curr_ema = ema.iloc[-1]
        curr_atr = atr.iloc[-1]

        # Determine regime
        if curr_rsi < self.rsi_oversold:
            regime = "oversold"
        elif curr_rsi > self.rsi_overbought:
            regime = "overbought"
        else:
            # Check EMA slope/trend
            ema_slope = (ema.iloc[-1] - ema.iloc[-5]) / ema.iloc[-5]
            if abs(ema_slope) > 0.002:
                regime = "trending"
            else:
                regime = "ranging"

        buy_score = 0
        sell_score = 0
        buy_reasons = []
        sell_reasons = []

        # ---------------- BULLISH MEAN REVERSION (BUY) ----------------
        # 1. RSI Extreme: RSI is below oversold threshold (default 30)
        if curr_rsi <= self.rsi_oversold or prev_rsi <= self.rsi_oversold:
            buy_score += 25
            buy_reasons.append(f"RSI oversold ({curr_rsi:.1f} <= {self.rsi_oversold}) (+25)")
        
        # 2. RSI Direction: RSI has hooked up/turned back toward neutral
        if curr_rsi > prev_rsi:
            buy_score += 25
            buy_reasons.append("RSI turning back up (+25)")

        # 3. Mean Proximity: Price is close to EMA50 (within 1.5 ATR)
        distance = abs(curr_close - curr_ema)
        if distance <= self.proximity_limit_atr * curr_atr:
            buy_score += 25
            buy_reasons.append(f"Price near EMA50 ({distance:.2f} <= {self.proximity_limit_atr * curr_atr:.2f}) (+25)")

        # 4. Candle Confirmation: Close > Open (bullish body)
        if curr_close > curr_open:
            buy_score += 25
            buy_reasons.append("Bullish candle body confirms (+25)")

        # ---------------- BEARISH MEAN REVERSION (SELL) ----------------
        # 1. RSI Extreme: RSI is above overbought threshold (default 70)
        if curr_rsi >= self.rsi_overbought or prev_rsi >= self.rsi_overbought:
            sell_score += 25
            sell_reasons.append(f"RSI overbought ({curr_rsi:.1f} >= {self.rsi_overbought}) (+25)")
            
        # 2. RSI Direction: RSI has hooked down/turned back toward neutral
        if curr_rsi < prev_rsi:
            sell_score += 25
            sell_reasons.append("RSI turning back down (+25)")

        # 3. Mean Proximity: Price within 1.5 ATR of EMA50
        if distance <= self.proximity_limit_atr * curr_atr:
            sell_score += 25
            sell_reasons.append(f"Price near EMA50 ({distance:.2f} <= {self.proximity_limit_atr * curr_atr:.2f}) (+25)")

        # 4. Candle Confirmation: Close < Open (bearish body)
        if curr_close < curr_open:
            sell_score += 25
            sell_reasons.append("Bearish candle body confirms (+25)")

        # Compile reasons
        reasons = []
        if buy_score > 0:
            reasons.append(f"Buy: {', '.join(buy_reasons)}")
        if sell_score > 0:
            reasons.append(f"Sell: {', '.join(sell_reasons)}")

        reason_str = "; ".join(reasons) if reasons else "No mean reversion signals"

        return StrategySignal(buy_score, sell_score, regime, reason_str)
