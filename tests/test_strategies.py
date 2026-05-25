import unittest
import pandas as pd
import numpy as np
from hyperbot.strategies import (
    EmaTrendPullback,
    RsiMeanReversion,
    BollingerBandSqueeze,
    FairValueGap,
    MacdMomentum,
    StrategySignal
)
from hyperbot.aggregator import SignalAggregator

class TestTradingStrategies(unittest.TestCase):
    def setUp(self):
        # Create a mock dataframe of 300 candles representing an uptrend
        dates = pd.date_range(start="2026-01-01", periods=300, freq="15min")
        
        # Simple linear uptrend with noise
        np.random.seed(42)
        close_prices = 100.0 + np.cumsum(np.random.normal(0.2, 0.5, 300))
        open_prices = close_prices - np.random.normal(0.0, 0.2, 300)
        high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.normal(0.1, 0.1, 300))
        low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.normal(0.1, 0.1, 300))
        volume = np.random.randint(100, 1000, 300).astype(float)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume
        })
        
        # Central configs
        self.config = {
            'agree_threshold': 50,
            'min_agree': 3,
            'strategies': {
                'ema_trend': {'fast_period': 20, 'slow_period': 200, 'atr_period': 14, 'pullback_limit_atr': 0.5},
                'rsi_meanrev': {'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70, 'ema_period': 50, 'proximity_limit_atr': 1.5},
                'bb_squeeze': {'bb_period': 20, 'bb_std': 2.0, 'volatility_history': 50, 'volatility_percentile': 30, 'volume_sma_period': 20},
                'fvg': {'lookback': 50, 'fresh_bars': 15, 'proximity_atr': 0.25, 'min_gap_atr': 0.08, 'ema_period': 200},
                'macd_momentum': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'ema_period': 200, 'fresh_crossover_bars': 3}
            }
        }

    def test_ema_trend_strategy(self):
        strat = EmaTrendPullback(self.config['strategies']['ema_trend'])
        sig = strat.analyze(self.df)
        
        self.assertIsInstance(sig, StrategySignal)
        self.assertTrue(0 <= sig.buy_confidence <= 100)
        self.assertTrue(0 <= sig.sell_confidence <= 100)
        self.assertIn(sig.regime, ["uptrend", "downtrend", "transitioning"])

    def test_rsi_meanrev_strategy(self):
        strat = RsiMeanReversion(self.config['strategies']['rsi_meanrev'])
        sig = strat.analyze(self.df)
        
        self.assertIsInstance(sig, StrategySignal)
        self.assertTrue(0 <= sig.buy_confidence <= 100)
        self.assertTrue(0 <= sig.sell_confidence <= 100)
        self.assertIn(sig.regime, ["oversold", "overbought", "ranging", "trending"])

    def test_bb_squeeze_strategy(self):
        strat = BollingerBandSqueeze(self.config['strategies']['bb_squeeze'])
        sig = strat.analyze(self.df)
        
        self.assertIsInstance(sig, StrategySignal)
        self.assertTrue(0 <= sig.buy_confidence <= 100)
        self.assertTrue(0 <= sig.sell_confidence <= 100)
        self.assertIn(sig.regime, ["squeeze", "expansion", "normal"])

    def test_fvg_strategy(self):
        strat = FairValueGap(self.config['strategies']['fvg'])
        sig = strat.analyze(self.df)
        
        self.assertIsInstance(sig, StrategySignal)
        self.assertTrue(0 <= sig.buy_confidence <= 100)
        self.assertTrue(0 <= sig.sell_confidence <= 100)

    def test_macd_momentum_strategy(self):
        strat = MacdMomentum(self.config['strategies']['macd_momentum'])
        sig = strat.analyze(self.df)
        
        self.assertIsInstance(sig, StrategySignal)
        self.assertTrue(0 <= sig.buy_confidence <= 100)
        self.assertTrue(0 <= sig.sell_confidence <= 100)
        self.assertIn(sig.regime, ["momentum_up", "momentum_down", "neutral"])

    def test_aggregator(self):
        agg = SignalAggregator(self.config)
        rec, signals, metrics = agg.aggregate(self.df)
        
        self.assertIn(rec, ["long", "short", "stand_aside"])
        self.assertEqual(len(signals), 5)
        self.assertIn('agree_buy', metrics)
        self.assertIn('agree_sell', metrics)

if __name__ == "__main__":
    unittest.main()
