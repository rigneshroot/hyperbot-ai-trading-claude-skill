import argparse
import yaml
from hyperbot.exchange_client import HyperliquidClient
from hyperbot.aggregator import SignalAggregator

def run_analyzer():
    parser = argparse.ArgumentParser(description="Live read-only Market Analyzer for hyperbot")
    parser.add_argument("--symbol", type=str, default=None, help="Coin to analyze (e.g. BTC)")
    parser.add_argument("--interval", type=str, default=None, help="Candle interval (e.g. 15m)")
    args = parser.parse_args()

    # Load configuration
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    symbol = args.symbol or config.get('symbol', 'BTC')
    interval = args.interval or config.get('interval', '15m')
    
    threshold = config.get('agree_threshold', 50)
    min_agree = config.get('min_agree', 4)

    print(f"=========================================================================================")
    print(f"                      HYPERBOT LIVE MARKET REAL-TIME ANALYSIS                            ")
    print(f"                      Asset: {symbol} | Interval: {interval}                             ")
    print(f"=========================================================================================")

    # Initialize exchange client
    client = HyperliquidClient()
    
    # We fetch 250 candles to seed technical analysis warmup window (EMA200 requires 200+ candles)
    try:
        df = client.get_candles(symbol, interval, 250)
    except Exception as e:
        print(f"Error fetching candles: {str(e)}")
        return

    # Initialize aggregator
    aggregator = SignalAggregator(config)
    
    # Run strategies and consolidate recommendation
    recommendation, signals, metrics = aggregator.aggregate(df)

    # Format and print strategies breakdown in an elegant table
    header = f"{'Strategy Name':<22} | {'Buy %':<5} | {'Sell %':<6} | {'Regime':<13} | {'Reason Breakdown'}"
    print(header)
    print("-" * 110)

    for name, sig in signals.items():
        # Capitalize and format name
        clean_name = name.replace("_", " ").title()
        
        # Add asterisk if score meets threshold
        b_ast = "*" if sig.buy_confidence >= threshold else " "
        s_ast = "*" if sig.sell_confidence >= threshold else " "
        
        b_str = f"{sig.buy_confidence}%{b_ast}"
        s_str = f"{sig.sell_confidence}%{s_ast}"
        
        # Truncate reason if too long
        reason = sig.reason
        if len(reason) > 60:
            reason = reason[:57] + "..."

        print(f"{clean_name:<22} | {b_str:<5} | {s_str:<6} | {sig.regime:<13} | {reason}")

    print("-" * 110)
    
    # Format recommendation output
    rec_colors = {
        'long': '\033[92mLONG\033[0m',       # Green
        'short': '\033[91mSHORT\033[0m',     # Red
        'stand_aside': '\033[93mSTAND ASIDE\033[0m' # Yellow
    }
    
    # Fallback to plain text if color output is not desired, but let's make it look premium
    rec_text = recommendation.upper()
    
    print(f"\nConsolidated Recommendation:  \033[1m{rec_text}\033[0m")
    print(f"Agree Buy:                   {metrics['agree_buy']}/5 strategies")
    print(f"Agree Sell:                  {metrics['agree_sell']}/5 strategies")
    print(f"Average Buy Score:           {metrics['avg_buy']:.1f}%")
    print(f"Average Sell Score:          {metrics['avg_sell']:.1f}%")
    print(f"Minimum Agreement Required:  {min_agree}/5 (each >= {threshold}%)")
    print(f"=========================================================================================")
    print("NOTE: This script operates in READ-ONLY mode. No orders have been placed.")
    print(f"=========================================================================================")

if __name__ == "__main__":
    run_analyzer()
