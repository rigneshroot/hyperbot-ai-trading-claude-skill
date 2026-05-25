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
from hyperbot.rationale_engine import TradeRationaleEngine, TradeRationale
from hyperbot.risk_context import RiskContextLayer, RiskAssessment, RISK_PROFILES
from hyperbot.institutional_context import InstitutionalContextProvider, InstitutionalContext

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


class TestTradeRationaleEngine(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range(start="2026-01-01", periods=300, freq="15min")
        close_prices = 100.0 + np.cumsum(np.random.normal(0.2, 0.5, 300))
        open_prices = close_prices - np.random.normal(0.0, 0.2, 300)
        high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.normal(0.1, 0.1, 300))
        low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.normal(0.1, 0.1, 300))
        volume = np.random.randint(100, 1000, 300).astype(float)

        self.df = pd.DataFrame({
            'timestamp': dates, 'open': open_prices, 'high': high_prices,
            'low': low_prices, 'close': close_prices, 'volume': volume
        })
        self.config = {
            'agree_threshold': 50, 'min_agree': 3,
            'strategies': {
                'ema_trend': {'fast_period': 20, 'slow_period': 200, 'atr_period': 14, 'pullback_limit_atr': 0.5},
                'rsi_meanrev': {'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70, 'ema_period': 50, 'proximity_limit_atr': 1.5},
                'bb_squeeze': {'bb_period': 20, 'bb_std': 2.0, 'volatility_history': 50, 'volatility_percentile': 30, 'volume_sma_period': 20},
                'fvg': {'lookback': 50, 'fresh_bars': 15, 'proximity_atr': 0.25, 'min_gap_atr': 0.08, 'ema_period': 200},
                'macd_momentum': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'ema_period': 200, 'fresh_crossover_bars': 3}
            }
        }

    def test_rationale_engine_returns_valid_rationale(self):
        engine = TradeRationaleEngine(self.config)
        rationale = engine.analyse(self.df, "BTC", "15m", account_risk_pct=1.0)

        self.assertIsInstance(rationale, TradeRationale)
        self.assertEqual(rationale.symbol, "BTC")
        self.assertEqual(rationale.interval, "15m")
        self.assertIn(rationale.direction, ["long", "short", "no_setup"])
        self.assertTrue(0 <= rationale.confidence_score <= 100)
        self.assertTrue(0 <= rationale.strategies_agreed <= 5)
        self.assertIsInstance(rationale.invalidity_conditions, list)
        self.assertIsInstance(rationale.strategy_breakdown, dict)
        self.assertEqual(len(rationale.strategy_breakdown), 5)

    def test_rationale_display_produces_string(self):
        engine = TradeRationaleEngine(self.config)
        rationale = engine.analyse(self.df, "ETH", "5m")
        output = rationale.display()

        self.assertIsInstance(output, str)
        self.assertIn("Trade Rationale", output)
        self.assertIn("ETH", output)

    def test_rationale_position_sizing_capped(self):
        engine = TradeRationaleEngine(self.config)
        rationale = engine.analyse(self.df, "BTC", "15m", account_risk_pct=1.0)

        self.assertLessEqual(rationale.position_sizing_pct, 25.0)
        self.assertGreaterEqual(rationale.position_sizing_pct, 0.0)


class TestRiskContextLayer(unittest.TestCase):
    def test_all_profiles_exist(self):
        for name in ["conservative", "moderate", "aggressive"]:
            self.assertIn(name, RISK_PROFILES)

    def test_conservative_caps_position(self):
        layer = RiskContextLayer(profile_name="conservative", daily_pnl_pct=0.0)
        assessment = layer.evaluate(
            proposed_position_pct=20.0,
            risk_reward=3.0,
            confidence_score=80,
            strategies_agreed=4,
        )
        self.assertIsInstance(assessment, RiskAssessment)
        self.assertLessEqual(assessment.adjusted_position_pct, 5.0)
        self.assertTrue(len(assessment.warnings) > 0)

    def test_daily_loss_limit_blocks_entry(self):
        layer = RiskContextLayer(profile_name="moderate", daily_pnl_pct=-4.5)
        assessment = layer.evaluate(
            proposed_position_pct=10.0,
            risk_reward=2.5,
            confidence_score=70,
            strategies_agreed=4,
        )
        self.assertFalse(assessment.approved)
        self.assertEqual(assessment.adjusted_position_pct, 0.0)

    def test_low_rr_rejected(self):
        layer = RiskContextLayer(profile_name="conservative", daily_pnl_pct=0.0)
        assessment = layer.evaluate(
            proposed_position_pct=3.0,
            risk_reward=1.0,
            confidence_score=70,
            strategies_agreed=4,
        )
        self.assertFalse(assessment.approved)

    def test_low_agreement_rejected(self):
        layer = RiskContextLayer(profile_name="aggressive", daily_pnl_pct=0.0)
        assessment = layer.evaluate(
            proposed_position_pct=5.0,
            risk_reward=3.0,
            confidence_score=60,
            strategies_agreed=2,
        )
        self.assertFalse(assessment.approved)

    def test_valid_setup_passes_moderate(self):
        layer = RiskContextLayer(profile_name="moderate", daily_pnl_pct=0.0)
        assessment = layer.evaluate(
            proposed_position_pct=10.0,
            risk_reward=2.5,
            confidence_score=75,
            strategies_agreed=4,
        )
        self.assertTrue(assessment.approved)
        self.assertLessEqual(assessment.adjusted_position_pct, 15.0)

    def test_unknown_profile_defaults_to_moderate(self):
        layer = RiskContextLayer(profile_name="nonexistent")
        self.assertEqual(layer.profile_name, "moderate")

    def test_display_output(self):
        layer = RiskContextLayer(profile_name="conservative", daily_pnl_pct=0.0)
        assessment = layer.evaluate(
            proposed_position_pct=3.0,
            risk_reward=3.0,
            confidence_score=70,
            strategies_agreed=4,
        )
        output = assessment.display()
        self.assertIn("CONSERVATIVE", output)

    def test_list_profiles(self):
        output = RiskContextLayer.list_profiles()
        self.assertIn("conservative", output)
        self.assertIn("moderate", output)
        self.assertIn("aggressive", output)


class TestInstitutionalContext(unittest.TestCase):
    def test_known_symbol_returns_context(self):
        provider = InstitutionalContextProvider()
        ctx = provider.get_context("BTC")

        self.assertIsInstance(ctx, InstitutionalContext)
        self.assertEqual(ctx.symbol, "BTC")
        self.assertEqual(ctx.sector, "Digital Assets")
        self.assertFalse(ctx.live_feed_active)

    def test_unknown_symbol_returns_default(self):
        provider = InstitutionalContextProvider()
        ctx = provider.get_context("OBSCURECOIN")

        self.assertIsInstance(ctx, InstitutionalContext)
        self.assertEqual(ctx.sector, "Unknown")
        self.assertIn("No institutional context available", ctx.recent_signal)

    def test_live_feed_takes_priority(self):
        live_data = {
            "BTC": {
                "sector": "Crypto Majors",
                "institutional_flow": "accumulation",
                "recent_signal": "Live data from institutional feed",
                "macro_tailwind": "ETF inflows",
                "macro_headwind": None,
                "source": "institutional-finance-skills [live]",
            }
        }
        provider = InstitutionalContextProvider(live_feed=live_data)
        ctx = provider.get_context("BTC")

        self.assertTrue(ctx.live_feed_active)
        self.assertEqual(ctx.sector, "Crypto Majors")
        self.assertIn("Live data", ctx.recent_signal)

    def test_display_output(self):
        provider = InstitutionalContextProvider()
        ctx = provider.get_context("ETH")
        output = ctx.display()

        self.assertIn("ETH", output)
        self.assertIn("Institutional Context", output)

    def test_alignment_note_long_accumulation(self):
        provider = InstitutionalContextProvider()
        ctx = provider.get_context("ETH")
        note = ctx.alignment_note("long")
        self.assertIsInstance(note, str)
        self.assertTrue(len(note) > 10)

    def test_alignment_note_no_direction(self):
        provider = InstitutionalContextProvider()
        ctx = provider.get_context("BTC")
        note = ctx.alignment_note("neutral")
        self.assertIn("No institutional alignment", note)

    def test_case_insensitive_lookup(self):
        provider = InstitutionalContextProvider()
        ctx = provider.get_context("btc")
        self.assertEqual(ctx.symbol, "BTC")


if __name__ == "__main__":
    unittest.main()
