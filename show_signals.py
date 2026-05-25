import json
import os

def run_show_signals():
    results_file = "backtest_results.json"
    if not os.path.exists(results_file):
        print(f"Error: '{results_file}' not found. Run backtest.py first.")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    metadata = data.get('metadata', {})
    trades = data.get('trades', [])
    threshold = metadata.get('agree_threshold', 50)

    print(f"=========================================================================")
    print(f"                 PER-TRADE CONFIDENCE SCORES TABLE                       ")
    print(f"                 (Agree Threshold: {threshold}%)")
    print(f"=========================================================================")
    
    header = f"{'#':<4} | {'Time':<19} | {'Side':<5} | {'Out':<4} | {'EMA':<6} | {'RSI':<6} | {'BB':<6} | {'FVG':<6} | {'MACD':<6}"
    print(header)
    print("-" * len(header))

    for idx, t in enumerate(trades, 1):
        outcome = "WIN" if t['outcome'] == 'win' else "loss"
        side = t['side']
        time_str = t['entry_time'][:19].replace("T", " ")
        
        # Scores formatting, append asterisk if score >= threshold
        scores_fmt = {}
        for name in ['ema_trend', 'rsi_meanrev', 'bb_squeeze', 'fvg', 'macd_momentum']:
            score = t['scores'].get(name, 0)
            ast = "*" if score >= threshold else ""
            scores_fmt[name] = f"{ast}{score}%"

        print(f"{idx:<4} | {time_str:<19} | {side:<5} | {outcome:<4} | {scores_fmt['ema_trend']:<6} | {scores_fmt['rsi_meanrev']:<6} | {scores_fmt['bb_squeeze']:<6} | {scores_fmt['fvg']:<6} | {scores_fmt['macd_momentum']:<6}")
        
    print(f"=========================================================================")
    print(f"Total simulated trades: {len(trades)}")
    print(f"An asterisk (*) indicates the strategy met the {threshold}% threshold.")
    print(f"=========================================================================")

if __name__ == "__main__":
    run_show_signals()
