from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class StrategySignal:
    buy_confidence: int       # Score from 0 to 100
    sell_confidence: int      # Score from 0 to 100
    regime: str               # e.g., 'uptrend', 'squeeze', 'oversold'
    reason: str               # Explanatory text of the breakdown

class BaseStrategy:
    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """
        Processes candle data and returns a StrategySignal.
        Must be overridden by subclasses.
        """
        raise NotImplementedError("Strategies must implement the analyze method.")

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Wilder's smoothing or simple exponential moving average for ATR
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        return atr

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).copy()
        loss = (-delta.where(delta < 0, 0)).copy()
        
        # Wilder's smoothing
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
        sma = series.rolling(window=period).mean()
        rstd = series.rolling(window=period).std()
        
        upper_band = sma + (num_std * rstd)
        lower_band = sma - (num_std * rstd)
        band_width = (upper_band - lower_band) / sma
        
        return upper_band, sma, lower_band, band_width
