import os
import json
import argparse
import urllib.request
import urllib.parse
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from hyperbot.aggregator import SignalAggregator

def fetch_candles_paginated(symbol: str, interval: str, days: int, network: str = "testnet") -> pd.DataFrame:
    """
    Fetches historical candles from Hyperliquid with proper pagination.
    Hyperliquid API returns max 5000 candles per call.
    """
    base_url = "https://api.hyperliquid-testnet.xyz/info" if network == "testnet" else "https://api.hyperliquid.xyz/info"
    
    end_time_ms = int(datetime.utcnow().timestamp() * 1000)
    start_time_ms = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
    
    print(f"Fetching {days} days of {interval} candles for {symbol} on {network}...")
    
    all_candles = []
    current_end = end_time_ms
    
    while current_end > start_time_ms:
        req_body = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": interval,
                "startTime": start_time_ms,
                "endTime": current_end
            }
        }
        
        try:
            req_data = json.dumps(req_body).encode('utf-8')
            req = urllib.request.Request(
                base_url, 
                data=req_data, 
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            if not res_data or not isinstance(res_data, list):
                print(f"Error or empty response from Hyperliquid: {res_data}")
                break
                
            # Hyperliquid returns candles sorted by time
            # e.g., oldest to newest or vice versa. Usually oldest first.
            batch = res_data
            if len(batch) == 0:
                break
                
            # Filter candles that are within our range
            batch = [c for c in batch if c['t'] >= start_time_ms and c['t'] < current_end]
            if len(batch) == 0:
                break
                
            all_candles.extend(batch)
            
            # Find the oldest candle timestamp in this batch to move backward
            oldest_t = min(c['t'] for c in batch)
            
            # If we didn't move backward, break to avoid infinite loop
            if oldest_t >= current_end:
                break
                
            current_end = oldest_t
            print(f"Fetched {len(all_candles)} candles so far (moving back to {datetime.utcfromtimestamp(oldest_t/1000)})...")
            
        except Exception as e:
            print(f"Error fetching candle snapshot: {str(e)}")
            break
            
    if not all_candles:
        raise ValueError("No historical candles retrieved.")

    # Remove duplicates and sort by timestamp
    candle_dict = {c['t']: c for c in all_candles}
    sorted_ts = sorted(candle_dict.keys())
    
    records = []
    for ts in sorted_ts:
        c = candle_dict[ts]
        records.append({
            'timestamp': pd.to_datetime(c['t'], unit='ms'),
            'open': float(c['o']),
            'high': float(c['h']),
            'low': float(c['l']),
            'close': float(c['c']),
            'volume': float(c['v'])
        })
        
    df = pd.DataFrame(records)
    print(f"Completed fetching. Total unique candles retrieved: {len(df)}")
    return df

def run_backtest():
    parser = argparse.ArgumentParser(description="Walk-Forward Backtesting Engine for hyperbot")
    parser.add_argument("--symbol", type=str, default=None, help="Trading symbol (e.g. BTC)")
    parser.add_argument("--interval", type=str, default=None, help="Candle interval (e.g. 15m)")
    parser.add_argument("--days", type=int, default=None, help="Number of historical days to backtest")
    parser.add_argument("--confidence", type=int, default=None, help="Strategy agreement threshold (0-100)")
    parser.add_argument("--min-agree", type=int, default=None, help="Min strategies that must agree (1-5)")
    args = parser.parse_args()

    # Load configuration
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    # Override with CLI args if specified
    symbol = args.symbol or config.get('symbol', 'BTC')
    interval = args.interval or config.get('interval', '15m')
    days = args.days or config.get('default_days', 30)
    
    if args.confidence is not None:
        config['agree_threshold'] = args.confidence
    if args.min_agree is not None:
        config['min_agree'] = args.min_agree

    print(f"--- BACKTEST CONFIGURATION ---")
    print(f"Symbol:          {symbol}")
    print(f"Interval:        {interval}")
    print(f"Days:            {days}")
    print(f"Agree Threshold: {config['agree_threshold']}%")
    print(f"Min Agree:       {config['min_agree']}/5 strategies")
    print(f"------------------------------")

    # Fetch historical data
    df = fetch_candles_paginated(symbol, interval, days)
    
    # Initialize aggregator
    aggregator = SignalAggregator(config)
    
    # Pre-calculate ATR for stop sizing (using ATR14)
    df['atr'] = aggregator.strategies['ema_trend'].calculate_atr(df, 14)
    
    # Warmup period of 215 bars ensures EMA200 is seeded properly
    warmup_period = 215
    if len(df) <= warmup_period:
        print(f"Error: Not enough bars to satisfy the {warmup_period} bar warmup period.")
        return

    trades = []
    active_trade = None
    
    print("\nSimulating walk-forward backtest...")
    
    for idx in range(warmup_period, len(df)):
        # Feed only past data up to current bar to prevent lookahead
        sub_df = df.iloc[:idx+1]
        
        curr_bar = df.iloc[idx]
        curr_time = curr_bar['timestamp']
        curr_close = curr_bar['close']
        curr_high = curr_bar['high']
        curr_low = curr_bar['low']
        curr_atr = curr_bar['atr']
        
        # Check if we have an open trade
        if active_trade:
            side = active_trade['side']
            sl = active_trade['sl']
            tp = active_trade['tp']
            
            hit_sl = False
            hit_tp = False
            
            if side == 'long':
                if curr_low <= sl:
                    hit_sl = True
                if curr_high >= tp:
                    hit_tp = True
                    
                # Tie-breaking: if both SL and TP hit in same bar, count as loss
                if hit_sl and hit_tp:
                    active_trade['outcome'] = 'loss'
                    active_trade['exit_price'] = sl
                    active_trade['exit_time'] = curr_time.isoformat()
                    active_trade['bars_held'] = idx - active_trade['entry_index']
                    trades.append(active_trade)
                    active_trade = None
                elif hit_sl:
                    active_trade['outcome'] = 'loss'
                    active_trade['exit_price'] = sl
                    active_trade['exit_time'] = curr_time.isoformat()
                    active_trade['bars_held'] = idx - active_trade['entry_index']
                    trades.append(active_trade)
                    active_trade = None
                elif hit_tp:
                    active_trade['outcome'] = 'win'
                    active_trade['exit_price'] = tp
                    active_trade['exit_time'] = curr_time.isoformat()
                    active_trade['bars_held'] = idx - active_trade['entry_index']
                    trades.append(active_trade)
                    active_trade = None
                    
            elif side == 'short':
                if curr_high >= sl:
                    hit_sl = True
                if curr_low <= tp:
                    hit_tp = True
                    
                if hit_sl and hit_tp:
                    active_trade['outcome'] = 'loss'
                    active_trade['exit_price'] = sl
                    active_trade['exit_time'] = curr_time.isoformat()
                    active_trade['bars_held'] = idx - active_trade['entry_index']
                    trades.append(active_trade)
                    active_trade = None
                elif hit_sl:
                    active_trade['outcome'] = 'loss'
                    active_trade['exit_price'] = sl
                    active_trade['exit_time'] = curr_time.isoformat()
                    active_trade['bars_held'] = idx - active_trade['entry_index']
                    trades.append(active_trade)
                    active_trade = None
                elif hit_tp:
                    active_trade['outcome'] = 'win'
                    active_trade['exit_price'] = tp
                    active_trade['exit_time'] = curr_time.isoformat()
                    active_trade['bars_held'] = idx - active_trade['entry_index']
                    trades.append(active_trade)
                    active_trade = None
            continue
            
        # If no active trade, query the aggregator for signals
        recommendation, signals, metrics = aggregator.aggregate(sub_df)
        
        if recommendation in ['long', 'short']:
            # Calculate stop distance: 1.5 x ATR
            stop_distance = 1.5 * curr_atr
            
            # Require minimum ATR to avoid entering dead markets
            if curr_atr <= 0:
                continue
                
            if recommendation == 'long':
                sl = curr_close - stop_distance
                tp = curr_close + (2.0 * stop_distance) # 1:2 Risk-to-Reward ratio
            else: # short
                sl = curr_close + stop_distance
                tp = curr_close - (2.0 * stop_distance)

            # Record per-strategy confidence scores
            scores = {name: sig.buy_confidence if recommendation == 'long' else sig.sell_confidence
                      for name, sig in signals.items()}
            
            active_trade = {
                'entry_index': idx,
                'entry_time': curr_time.isoformat(),
                'side': recommendation,
                'entry_price': curr_close,
                'sl': sl,
                'tp': tp,
                'atr': curr_atr,
                'strategies_agreed': metrics['agree_buy'] if recommendation == 'long' else metrics['agree_sell'],
                'scores': scores,
                'exit_time': None,
                'exit_price': None,
                'outcome': None,
                'bars_held': 0
            }

    # If backtest ends with open trade, discard it (unrealized)
    if active_trade:
        print(f"Discarding final open trade at end of backtest window.")
        
    print(f"\nBacktest completed! Simulating {len(trades)} executed trades.")
    
    # Calculate performance metrics
    if trades:
        wins = [t for t in trades if t['outcome'] == 'win']
        losses = [t for t in trades if t['outcome'] == 'loss']
        win_rate = (len(wins) / len(trades)) * 100
        
        # Calculate individual trade unleveraged returns
        trade_returns = []
        for t in trades:
            # percent_move = (1.5 * atr) / entry_price
            percent_move = (1.5 * t['atr']) / t['entry_price']
            if t['outcome'] == 'win':
                trade_returns.append(2.0 * percent_move * 100.0)
            else:
                trade_returns.append(-1.0 * percent_move * 100.0)
                
        avg_win = sum([r for r in trade_returns if r > 0]) / len(wins) if wins else 0.0
        avg_loss = sum([r for r in trade_returns if r < 0]) / len(losses) if losses else 0.0
        
        gross_wins = sum([r for r in trade_returns if r > 0])
        gross_losses = sum([abs(r) for r in trade_returns if r < 0])
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else float('inf')
        
        print(f"--- RESULTS ---")
        print(f"Total Trades:       {len(trades)}")
        print(f"Wins:               {len(wins)}")
        print(f"Losses:             {len(losses)}")
        print(f"Win Rate:           {win_rate:.2f}%")
        print(f"Avg Win (Unlev):    {avg_win:+.2f}%")
        print(f"Avg Loss (Unlev):   {avg_loss:+.2f}%")
        print(f"Profit Factor:      {profit_factor:.2f}")
        print(f"--------------")
    else:
        print("No trades triggered during backtest.")

    # Save to backtest_results.json
    results = {
        'metadata': {
            'symbol': symbol,
            'interval': interval,
            'days': days,
            'agree_threshold': config['agree_threshold'],
            'min_agree': config['min_agree']
        },
        'trades': trades
    }
    
    with open("backtest_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("Full backtest details saved to 'backtest_results.json'.")

if __name__ == "__main__":
    run_backtest()
