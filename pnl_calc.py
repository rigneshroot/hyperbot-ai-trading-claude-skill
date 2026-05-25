import json
import os

def run_pnl_calc():
    results_file = "backtest_results.json"
    if not os.path.exists(results_file):
        print(f"Error: '{results_file}' not found. Please run backtest.py first to generate results.")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    metadata = data.get('metadata', {})
    trades = data.get('trades', [])

    print(f"--- PNL CALCULATION MATRIX ---")
    print(f"Backtest Run:    {metadata.get('symbol')} ({metadata.get('interval')}) over {metadata.get('days')} days")
    print(f"Agree Threshold: {metadata.get('agree_threshold')}% (min agree: {metadata.get('min_agree')}/5)")
    print(f"Total Trades:    {len(trades)}")
    print(f"------------------------------\n")

    if not trades:
        print("No trades triggered to simulate.")
        return

    scenarios = {
        "Scenario A (Split Sizing: 4/5 = 10%, 5/5 = 30%)": {
            "condition": lambda t: True,
            "size_fn": lambda t: 0.30 if t['strategies_agreed'] == 5 else 0.10
        },
        "Scenario B (5/5 Unanimous Only @ 20%)": {
            "condition": lambda t: t['strategies_agreed'] == 5,
            "size_fn": lambda t: 0.20
        },
        "Scenario C (Flat 20% Sizing on All Trades)": {
            "condition": lambda t: True,
            "size_fn": lambda t: 0.20
        },
        "Scenario D (Flat 30% Sizing on All Trades)": {
            "condition": lambda t: True,
            "size_fn": lambda t: 0.30
        }
    }

    start_balance = 10000.0
    leverage = 10.0

    for name, s_config in scenarios.items():
        balance = start_balance
        peak_balance = start_balance
        max_drawdown = 0.0
        wins = 0
        losses = 0
        total_executed = 0
        
        gross_wins = 0.0
        gross_losses = 0.0
        
        trade_returns_pct = []
        outcomes = []

        for t in trades:
            if not s_config["condition"](t):
                continue
                
            total_executed += 1
            balance_before = balance
            
            # Sizing is a fraction of current balance
            allocation = s_config["size_fn"](t)
            trade_size_usd = balance * allocation * leverage
            
            # PnL calculations based on stop distance relative to entry price
            # stop distance = 1.5 * ATR
            # long win = +2x stop distance, long loss = -1x stop distance
            # short win = +2x stop distance, short loss = -1x stop distance
            entry_price = t['entry_price']
            atr = t['atr']
            stop_distance = 1.5 * atr
            
            percent_move = stop_distance / entry_price
            
            if t['outcome'] == 'win':
                wins += 1
                trade_pnl = trade_size_usd * (2.0 * percent_move) # 1:2 Risk to Reward
                gross_wins += trade_pnl
                outcomes.append('win')
            else:
                losses += 1
                trade_pnl = -trade_size_usd * (1.0 * percent_move)
                gross_losses += abs(trade_pnl)
                outcomes.append('loss')

            # Update account balance
            balance += trade_pnl
            
            # Record percentage return of this trade relative to balance before trade
            ret_pct = (trade_pnl / balance_before) * 100.0
            trade_returns_pct.append(ret_pct)
            
            # Track peak and drawdowns
            if balance > peak_balance:
                peak_balance = balance
                
            dd = (peak_balance - balance) / peak_balance * 100.0
            if dd > max_drawdown:
                max_drawdown = dd

        # Print Scenario Summary and Return Distribution Analysis
        return_pct = ((balance - start_balance) / start_balance) * 100.0
        win_rate = (wins / total_executed * 100) if total_executed > 0 else 0.0
        
        # Statistical Distribution Metrics
        avg_win_pct = sum([r for r in trade_returns_pct if r > 0]) / wins if wins > 0 else 0.0
        avg_loss_pct = sum([r for r in trade_returns_pct if r < 0]) / losses if losses > 0 else 0.0
        win_loss_ratio = abs(avg_win_pct / avg_loss_pct) if avg_loss_pct != 0 else 0.0
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else float('inf')
        
        # Mean & Std Dev
        mean_ret = sum(trade_returns_pct) / total_executed if total_executed > 0 else 0.0
        variance = sum((r - mean_ret) ** 2 for r in trade_returns_pct) / (total_executed - 1) if total_executed > 1 else 0.0
        std_dev = variance ** 0.5
        
        # Sharpe Ratio (per-trade base, normalized)
        sharpe = (mean_ret / std_dev) if std_dev > 0 else 0.0
        
        # Sortino Ratio (Downside deviation base)
        downside_variance = sum((r - mean_ret) ** 2 for r in trade_returns_pct if r < 0) / (total_executed - 1) if total_executed > 1 else 0.0
        downside_std_dev = downside_variance ** 0.5
        sortino = (mean_ret / downside_std_dev) if downside_std_dev > 0 else 0.0
        
        # Streaks
        consec_wins = 0
        consec_losses = 0
        max_consec_wins = 0
        max_consec_losses = 0
        for out in outcomes:
            if out == 'win':
                consec_wins += 1
                consec_losses = 0
                if consec_wins > max_consec_wins:
                    max_consec_wins = consec_wins
            else:
                consec_losses += 1
                consec_wins = 0
                if consec_losses > max_consec_losses:
                    max_consec_losses = consec_losses

        # ASCII Return Distribution Histogram Buckets
        buckets = {
            "<-5.0%      ": 0,
            "-5.0%..-2.5%": 0,
            "-2.5%..0.0% ": 0,
            "0.0%..2.5%  ": 0,
            "2.5%..5.0%  ": 0,
            ">5.0%       ": 0
        }
        for r in trade_returns_pct:
            if r < -5.0:
                buckets["<-5.0%      "] += 1
            elif -5.0 <= r < -2.5:
                buckets["-5.0%..-2.5%"] += 1
            elif -2.5 <= r < 0.0:
                buckets["-2.5%..0.0% "] += 1
            elif 0.0 <= r < 2.5:
                buckets["0.0%..2.5%  "] += 1
            elif 2.5 <= r < 5.0:
                buckets["2.5%..5.0%  "] += 1
            else:
                buckets[">5.0%       "] += 1

        print(f"=== {name} ===")
        print(f"Executed Trades: {total_executed}")
        print(f"Win Rate:        {win_rate:.2f}% (Wins: {wins}, Losses: {losses})")
        print(f"Starting Equity: ${start_balance:,.2f}")
        print(f"Ending Equity:   ${balance:,.2f}")
        print(f"Total Return:    {return_pct:+.2f}%")
        print(f"Max Drawdown:    {max_drawdown:.2f}%")
        print(f"Gross Wins:      ${gross_wins:,.2f} | Gross Losses: ${gross_losses:,.2f}")
        print(f"Profit Factor:   {profit_factor:.2f}")
        print(f"-----------------------------------------")
        print(f"DISTRIBUTION METRICS:")
        print(f"  Avg Win:       {avg_win_pct:+.2f}%")
        print(f"  Avg Loss:      {avg_loss_pct:+.2f}%")
        print(f"  Win/Loss Ratio:{win_loss_ratio:.2f}x")
        print(f"  Mean Return:   {mean_ret:+.2f}%")
        print(f"  Std Dev:       {std_dev:.2f}%")
        print(f"  Sharpe Ratio:  {sharpe:.3f}")
        print(f"  Sortino Ratio: {sortino:.3f}")
        print(f"  Max Win Streak: {max_consec_wins} trades")
        print(f"  Max Loss Streak:{max_consec_losses} trades")
        print(f"-----------------------------------------")
        print(f"RETURN DISTRIBUTION:")
        for label, count in buckets.items():
            stars = "*" * count
            print(f"  {label} : [{count:>3}] {stars}")
        print(f"=========================================\n")

if __name__ == "__main__":
    run_pnl_calc()
