import pandas as pd
from .base import BaseStrategy, StrategySignal

class MacdMomentum(BaseStrategy):
    def __init__(self, params: dict):
        super().__init__("MACD Momentum", params)
        self.fast_period = params.get('fast_period', 12)
        self.slow_period = params.get('slow_period', 26)
        self.signal_period = params.get('signal_period', 9)
        self.ema_period = params.get('ema_period', 200)
        self.fresh_crossover_bars = params.get('fresh_crossover_bars', 3)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        if len(df) < max(self.slow_period + self.signal_period, self.ema_period) + 5:
            return StrategySignal(0, 0, "neutral", "Insufficient data for MACD Momentum")

        close = df['close']
        
        # Calculate MACD
        ema_fast = self.calculate_ema(close, self.fast_period)
        ema_slow = self.calculate_ema(close, self.slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, self.signal_period)
        hist = macd_line - signal_line

        # Calculate EMA200
        ema_200 = self.calculate_ema(close, self.ema_period)

        # Get values for current and historical analysis
        curr_close = close.iloc[-1]
        curr_macd = macd_line.iloc[-1]
        curr_signal = signal_line.iloc[-1]
        curr_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2]
        curr_ema200 = ema_200.iloc[-1]

        # Check for fresh crossovers in the last N bars
        fresh_bull_crossover = False
        fresh_bear_crossover = False

        for k in range(1, self.fresh_crossover_bars + 1):
            idx = -k
            if idx - 1 < -len(df):
                break
            # Crossover check: MACD crosses signal line
            prev_macd_val = macd_line.iloc[idx - 1]
            prev_signal_val = signal_line.iloc[idx - 1]
            curr_macd_val = macd_line.iloc[idx]
            curr_signal_val = signal_line.iloc[idx]
            
            if prev_macd_val <= prev_signal_val and curr_macd_val > curr_signal_val:
                fresh_bull_crossover = True
                break
            elif prev_macd_val >= prev_signal_val and curr_macd_val < curr_signal_val:
                fresh_bear_crossover = True
                break

        # Determine regime
        if curr_macd > curr_signal and curr_hist > 0:
            regime = "momentum_up"
        elif curr_macd < curr_signal and curr_hist < 0:
            regime = "momentum_down"
        else:
            regime = "neutral"

        buy_score = 0
        sell_score = 0
        buy_reasons = []
        sell_reasons = []

        # ---------------- BULLISH momentum (BUY) ----------------
        # 1. Price above EMA200
        if curr_close > curr_ema200:
            buy_score += 25
            buy_reasons.append("Price > EMA200 (HTF bullish) (+25)")
            
        # 2. MACD Line > Signal Line
        if curr_macd > curr_signal:
            buy_score += 25
            buy_reasons.append("MACD > Signal line (+25)")
            
        # 3. Histogram positive & accelerating (larger than previous bar)
        if curr_hist > 0 and curr_hist > prev_hist:
            buy_score += 25
            buy_reasons.append(f"Hist positive & accelerating ({curr_hist:.4f} > {prev_hist:.4f}) (+25)")
        elif curr_hist > 0: # positive but slowing down
            buy_score += 12
            buy_reasons.append("Hist positive but decelerating (+12)")
            
        # 4. Fresh crossover within last 3 bars
        if fresh_bull_crossover:
            buy_score += 25
            buy_reasons.append(f"Fresh bull crossover within {self.fresh_crossover_bars} bars (+25)")

        # ---------------- BEARISH momentum (SELL) ----------------
        # 1. Price below EMA200
        if curr_close < curr_ema200:
            sell_score += 25
            sell_reasons.append("Price < EMA200 (HTF bearish) (+25)")
            
        # 2. MACD Line < Signal Line
        if curr_macd < curr_signal:
            sell_score += 25
            sell_reasons.append("MACD < Signal line (+25)")
            
        # 3. Histogram negative & accelerating (more negative than previous bar)
        if curr_hist < 0 and curr_hist < prev_hist:
            sell_score += 25
            sell_reasons.append(f"Hist negative & accelerating ({curr_hist:.4f} < {prev_hist:.4f}) (+25)")
        elif curr_hist < 0: # negative but slowing down
            sell_score += 12
            sell_reasons.append("Hist negative but decelerating (+12)")
            
        # 4. Fresh crossover within last 3 bars
        if fresh_bear_crossover:
            sell_score += 25
            sell_reasons.append(f"Fresh bear crossover within {self.fresh_crossover_bars} bars (+25)")

        # Compile reasons
        reasons = []
        if buy_score > 0:
            reasons.append(f"Buy: {', '.join(buy_reasons)}")
        if sell_score > 0:
            reasons.append(f"Sell: {', '.join(sell_reasons)}")

        reason_str = "; ".join(reasons) if reasons else "No MACD momentum signals"

        return StrategySignal(buy_score, sell_score, regime, reason_str)
