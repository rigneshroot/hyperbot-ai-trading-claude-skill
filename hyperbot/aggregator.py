import pandas as pd
from typing import Dict, List, Tuple
from .strategies import (
    EmaTrendPullback,
    RsiMeanReversion,
    BollingerBandSqueeze,
    FairValueGap,
    MacdMomentum,
    StrategySignal
)

class SignalAggregator:
    def __init__(self, config: dict):
        self.config = config
        self.agree_threshold = config.get('agree_threshold', 50)
        self.min_agree = config.get('min_agree', 3)
        
        # Initialize strategies with their respective configs
        strat_configs = config.get('strategies', {})
        self.strategies = {
            'ema_trend': EmaTrendPullback(strat_configs.get('ema_trend', {})),
            'rsi_meanrev': RsiMeanReversion(strat_configs.get('rsi_meanrev', {})),
            'bb_squeeze': BollingerBandSqueeze(strat_configs.get('bb_squeeze', {})),
            'fvg': FairValueGap(strat_configs.get('fvg', {})),
            'macd_momentum': MacdMomentum(strat_configs.get('macd_momentum', {}))
        }

    def aggregate(self, df: pd.DataFrame) -> Tuple[str, Dict[str, StrategySignal], dict]:
        """
        Runs all 5 strategies on the dataframe and aggregates their signals.
        Returns:
            recommendation: 'long', 'short', or 'stand_aside'
            signals: Dict of strategy_name -> StrategySignal
            metrics: dict of intermediate calculations (agree counts, averages, etc.)
        """
        signals = {}
        agree_buy = 0
        agree_sell = 0
        
        buy_scores = []
        sell_scores = []

        for name, strategy in self.strategies.items():
            try:
                sig = strategy.analyze(df)
                signals[name] = sig
                
                # Extract scores
                b_score = sig.buy_confidence
                s_score = sig.sell_confidence
                
                buy_scores.append(b_score)
                sell_scores.append(s_score)

                # Check agreement
                if b_score >= self.agree_threshold:
                    agree_buy += 1
                if s_score >= self.agree_threshold:
                    agree_sell += 1
            except Exception as e:
                # Safe fallback
                signals[name] = StrategySignal(0, 0, "error", f"Error in strategy: {str(e)}")
                buy_scores.append(0)
                sell_scores.append(0)

        # Calculate averages
        avg_buy = sum(buy_scores) / len(buy_scores) if buy_scores else 0.0
        avg_sell = sum(sell_scores) / len(sell_scores) if sell_scores else 0.0

        recommendation = 'stand_aside'

        # Apply aggregator voting logic
        # 1. Bullish (Long) Conditions
        #    - Enough strategies agree (>= min_agree)
        #    - Average buy is strong enough (>= 80% of agree_threshold)
        #    - Average buy is meaningfully higher than average sell (+15)
        is_bullish = (
            agree_buy >= self.min_agree and
            avg_buy >= (self.agree_threshold * 0.8) and
            avg_buy > (avg_sell + 15)
        )

        # 2. Bearish (Short) Conditions
        is_bearish = (
            agree_sell >= self.min_agree and
            avg_sell >= (self.agree_threshold * 0.8) and
            avg_sell > (avg_buy + 15)
        )

        if is_bullish and not is_bearish:
            recommendation = 'long'
        elif is_bearish and not is_bullish:
            recommendation = 'short'

        metrics = {
            'agree_buy': agree_buy,
            'agree_sell': agree_sell,
            'avg_buy': avg_buy,
            'avg_sell': avg_sell,
            'agree_threshold': self.agree_threshold,
            'min_agree': self.min_agree
        }

        return recommendation, signals, metrics
