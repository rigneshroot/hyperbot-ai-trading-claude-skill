import pandas as pd
from .base import BaseStrategy, StrategySignal

class EmaTrendPullback(BaseStrategy):
    def __init__(self, params: dict):
        super().__init__("EMA Trend Pullback", params)
        self.fast_period = params.get('fast_period', 20)
        self.slow_period = params.get('slow_period', 200)
        self.atr_period = params.get('atr_period', 14)
        self.pullback_limit_atr = params.get('pullback_limit_atr', 0.5)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        if len(df) < max(self.slow_period, self.atr_period) + 5:
            return StrategySignal(0, 0, "transitioning", "Insufficient data for EMA Trend Pullback")

        # Calculate indicators
        close = df['close']
        open_price = df['open']
        ema_fast = self.calculate_ema(close, self.fast_period)
        ema_slow = self.calculate_ema(close, self.slow_period)
        atr = self.calculate_atr(df, self.atr_period)

        # Get latest values (last closed bar)
        curr_close = close.iloc[-1]
        curr_open = open_price.iloc[-1]
        curr_fast = ema_fast.iloc[-1]
        curr_slow = ema_slow.iloc[-1]
        curr_atr = atr.iloc[-1]

        # Determine regime
        if curr_fast > curr_slow and curr_close > curr_slow:
            regime = "uptrend"
        elif curr_fast < curr_slow and curr_close < curr_slow:
            regime = "downtrend"
        else:
            regime = "transitioning"

        # Initialize confidence scores
        buy_score = 0
        sell_score = 0
        buy_reasons = []
        sell_reasons = []

        # ---------------- BULLISH SETUP (BUY) ----------------
        # 1. HTF Trend: Price above EMA200
        if curr_close > curr_slow:
            buy_score += 25
            buy_reasons.append("Price > EMA200 (+25)")
        
        # 2. Trend Alignment: Fast EMA above Slow EMA
        if curr_fast > curr_slow:
            buy_score += 25
            buy_reasons.append("EMA20 > EMA200 (+25)")
            
        # 3. Pullback Zone: Price is close to Fast EMA (within 0.5 ATR)
        distance = abs(curr_close - curr_fast)
        if distance <= self.pullback_limit_atr * curr_atr:
            buy_score += 25
            buy_reasons.append(f"Price within pullback zone ({distance:.2f} <= {self.pullback_limit_atr * curr_atr:.2f}) (+25)")
            
        # 4. Candle direction: Bullish candle
        if curr_close > curr_open:
            buy_score += 25
            buy_reasons.append("Bullish candle body (+25)")

        # ---------------- BEARISH SETUP (SELL) ----------------
        # 1. HTF Trend: Price below EMA200
        if curr_close < curr_slow:
            sell_score += 25
            sell_reasons.append("Price < EMA200 (+25)")
        
        # 2. Trend Alignment: Fast EMA below Slow EMA
        if curr_fast < curr_slow:
            sell_score += 25
            sell_reasons.append("EMA20 < EMA200 (+25)")
            
        # 3. Pullback Zone: Price within 0.5 ATR of fast EMA
        if distance <= self.pullback_limit_atr * curr_atr:
            sell_score += 25
            sell_reasons.append(f"Price within pullback zone ({distance:.2f} <= {self.pullback_limit_atr * curr_atr:.2f}) (+25)")
            
        # 4. Candle direction: Bearish candle
        if curr_close < curr_open:
            sell_score += 25
            sell_reasons.append("Bearish candle body (+25)")

        # Compile reasons
        reasons = []
        if buy_score > 0:
            reasons.append(f"Buy: {', '.join(buy_reasons)}")
        if sell_score > 0:
            reasons.append(f"Sell: {', '.join(sell_reasons)}")
        
        reason_str = "; ".join(reasons) if reasons else "No trend pullback signals"

        return StrategySignal(buy_score, sell_score, regime, reason_str)
