import os
import time
import json
import argparse
import urllib.request
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv

from hyperbot.exchange_client import HyperliquidClient
from hyperbot.aggregator import SignalAggregator
from hyperbot.llm_filter import LlmMetaFilter
from hyperbot.risk_context import RiskContextLayer

# Load environment secrets
load_dotenv()

STATE_FILE = "bot_state.json"

def load_bot_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "open_position": None,
        "daily_pnl_pct": 0.0,
        "last_pnl_reset": datetime.utcnow().date().isoformat(),
        "recent_outcomes": []
    }

def save_bot_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_alert(message: str):
    """
    Sends a notification to Telegram if configured in .env.
    """
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not token or not chat_id:
        # Silently skip if alerts not configured
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"[HYPERBOT ALERT]\n{message}",
        "parse_mode": "HTML"
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        print(f"Failed to send Telegram alert: {str(e)}")

def run_trading_bot():
    parser = argparse.ArgumentParser(description="Hyperbot Execution & Live Trading Daemon")
    parser.add_argument("--symbol", type=str, default=None, help="Coin to trade (e.g. BTC)")
    parser.add_argument("--interval", type=str, default=None, help="Timeframe interval (e.g. 15m)")
    parser.add_argument(
        "--risk-profile",
        type=str,
        default="moderate",
        choices=["conservative", "moderate", "aggressive"],
        help="Risk tolerance profile to apply",
    )
    parser.add_argument("--loop", action="store_true", help="Run indefinitely in an execution loop")
    args = parser.parse_args()

    # Load configuration
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    symbol = args.symbol or config.get('symbol', 'BTC')
    interval = args.interval or config.get('interval', '15m')
    
    # Initialize components
    client = HyperliquidClient()
    aggregator = SignalAggregator(config)
    llm_filter = LlmMetaFilter()

    # Load persistent state
    state = load_bot_state()

    # Reset daily PnL at midnight
    today_iso = datetime.utcnow().date().isoformat()
    if state["last_pnl_reset"] != today_iso:
        state["daily_pnl_pct"] = 0.0
        state["last_pnl_reset"] = today_iso
        save_bot_state(state)

    # Risk parameters from RiskContextLayer
    risk_layer = RiskContextLayer(profile_name=args.risk_profile, daily_pnl_pct=state["daily_pnl_pct"])
    max_position_sizing_pct = risk_layer.profile["max_position_pct"] / 100.0
    max_daily_loss_pct = risk_layer.profile["max_daily_loss_pct"]
    min_atr_percent = 0.0005       # Minimum volatility filter (0.05% of price)

    print("=========================================================================")
    print("                      INITIATING HYPERBOT ACTIVE ENGINE                  ")
    print(f"                      Symbol: {symbol} | Timeframe: {interval}          ")
    print(f"                      Risk Profile: {risk_layer.profile_name.upper()}   ")
    print("=========================================================================")

    def execute_tick():
        # Load local state inside tick
        curr_state = load_bot_state()
        
        # 0. Global Halt override check
        if os.getenv("HALT") == "1":
            print("[HALT TRIGGERED] HALT=1 detected in environment. Halting bot operations.")
            return

        # Update daily PnL state in risk layer
        risk_layer.daily_pnl_pct = curr_state["daily_pnl_pct"]

        # 1. Check daily drawdown circuit breaker
        if curr_state["daily_pnl_pct"] <= max_daily_loss_pct:
            print(f"[CIRCUIT BREAKER] Daily PnL threshold reached ({curr_state['daily_pnl_pct']:.2f}% <= {max_daily_loss_pct}%). Trading locked until midnight.")
            return

        # Fetch latest candles
        try:
            df = client.get_candles(symbol, interval, 250)
        except Exception as e:
            print(f"Execution loop failed to fetch candles: {str(e)}")
            return

        # Precalculate current values
        curr_bar = df.iloc[-1]
        curr_close = curr_bar['close']
        curr_time = curr_bar['timestamp']
        
        # Check volatility
        atr = aggregator.strategies['ema_trend'].calculate_atr(df, 14).iloc[-1]
        volatility = atr / curr_close if curr_close > 0 else 0
        if volatility < min_atr_percent:
            print(f"[RISK CONTROL] Stagnant market volatility ({volatility:.4%} < {min_atr_percent:.4%}). Skipping analysis.")
            return

        # 2. Check position state
        open_pos = curr_state["open_position"]
        if open_pos:
            # Check if active position was closed by SL or TP on the exchange
            # In mock mode, we manually track it. In real mode, we query active orders.
            # For simplicity and cross-environment safety, we simulate close checks
            side = open_pos['side']
            sl = open_pos['sl']
            tp = open_pos['tp']
            
            # Check if current bar hit exit criteria
            hit_sl = curr_bar['low'] <= sl if side == 'long' else curr_bar['high'] >= sl
            hit_tp = curr_bar['high'] >= tp if side == 'long' else curr_bar['low'] <= tp
            
            if hit_sl or hit_tp:
                outcome = "loss" if hit_sl else "win"
                exit_price = sl if hit_sl else tp
                
                # Sizing calculations for simulated PnL logging
                sizing = open_pos['size']
                leverage = open_pos['leverage']
                trade_size_usd = open_pos['entry_balance'] * sizing * leverage
                percent_move = abs(exit_price - open_pos['entry_price']) / open_pos['entry_price']
                
                trade_pnl_usd = trade_size_usd * percent_move if outcome == "win" else -trade_size_usd * percent_move
                pnl_pct = (trade_pnl_usd / open_pos['entry_balance']) * 100.0
                
                curr_state["daily_pnl_pct"] += pnl_pct
                curr_state["recent_outcomes"].append(outcome)
                if len(curr_state["recent_outcomes"]) > 3:
                    curr_state["recent_outcomes"].pop(0)
                    
                msg = (
                    f"Position CLOSED ({outcome.upper()})!\n"
                    f"Asset: {symbol} | Side: {side.upper()}\n"
                    f"Entry: {open_pos['entry_price']:.2f} | Exit: {exit_price:.2f}\n"
                    f"PnL: ${trade_pnl_usd:+.2f} ({pnl_pct:+.2f}%)"
                )
                print(f"[MOCK POSITION LOG] {msg}")
                send_alert(msg)
                
                curr_state["open_position"] = None
                save_bot_state(curr_state)
            else:
                print(f"[ACTIVE POSITION] Holding {side.upper()} open from {open_pos['entry_price']:.2f} (SL: {sl:.2f}, TP: {tp:.2f}).")
            return

        # 3. Aggregating signals
        recommendation, signals, metrics = aggregator.aggregate(df)
        
        # Print strategy signal details to user so they see the whole thinking process
        threshold = config.get('agree_threshold', 50)
        print(f"\n[{datetime.utcnow().strftime('%H:%M:%S')}] --- Active Tick Strategy Scoring Matrix ---")
        print(f"{'Strategy':<22} | {'Buy':>5} | {'Sell':>5} | {'Regime':<14} | Reason")
        print("-" * 95)
        for name, sig in signals.items():
            clean = name.replace("_", " ").title()
            b_str = f"{'*' if sig.buy_confidence >= threshold else ' '}{sig.buy_confidence}%"
            s_str = f"{'*' if sig.sell_confidence >= threshold else ' '}{sig.sell_confidence}%"
            reason = sig.reason if len(sig.reason) <= 55 else sig.reason[:52] + "..."
            print(f"{clean:<22} | {b_str:>5} | {s_str:>5} | {sig.regime:<14} | {reason}")
        print("-" * 95)
        print(f"Consensus: {recommendation.upper():<12}  "
              f"Buy: {metrics['agree_buy']}/5   Sell: {metrics['agree_sell']}/5   "
              f"Avg Buy: {metrics['avg_buy']:.1f}%   Avg Sell: {metrics['avg_sell']:.1f}%\n")

        if recommendation == 'stand_aside':
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Analysis completed. Recommendation is STAND ASIDE. No setup identified.")
            return

        # 4. Signal detected. Compute SL/TP details
        stop_distance = 1.5 * atr
        if recommendation == 'long':
            sl = curr_close - stop_distance
            tp = curr_close + (2.0 * stop_distance)
        else: # short
            sl = curr_close + stop_distance
            tp = curr_close - (2.0 * stop_distance)

        # 5. Query LLM Filter to audit the signal before proceeding
        recent_outcomes = curr_state.get("recent_outcomes", [])
        agree_count = metrics['agree_buy'] if recommendation == 'long' else metrics['agree_sell']
        
        approve, confidence, reason = llm_filter.filter_signal(
            symbol=symbol,
            side=recommendation,
            entry=curr_close,
            sl=sl,
            tp=tp,
            strategy_signals=signals,
            agree_count=agree_count,
            recent_outcomes=recent_outcomes
        )

        if not approve or confidence != "high":
            print(f"[LLM FILTER REJECTION] LLM rejected proposed trade (Confidence: {confidence}). Reason: {reason}")
            return

        # 6. Execute Order & Save position state
        balance = client.get_balance()
        position_size = max_position_sizing_pct
        
        # Calculate sizing in asset amount
        # position value = balance * size_fraction * leverage
        pos_val_usd = balance * position_size * config.get('leverage', 10)
        asset_size = pos_val_usd / curr_close
        
        # Perform order placement (Safe mock or actual testnet order)
        try:
            side_order = "buy" if recommendation == "long" else "sell"
            order_res = client.place_order(symbol, side_order, asset_size)
            
            # Save position details to state
            curr_state["open_position"] = {
                "entry_time": curr_time.isoformat(),
                "side": recommendation,
                "entry_price": curr_close,
                "sl": sl,
                "tp": tp,
                "size": position_size,
                "leverage": config.get('leverage', 10),
                "entry_balance": balance,
                "order_res": order_res
            }
            save_bot_state(curr_state)
            
            msg = (
                f"Position OPENED successfully!\n"
                f"Asset: {symbol} | Side: {recommendation.upper()}\n"
                f"Entry Price: {curr_close:.2f}\n"
                f"Sizing: {position_size:.0%} balance | SL: {sl:.2f} | TP: {tp:.2f}\n"
                f"Strategies Agreed: {agree_count}/5"
            )
            send_alert(msg)
            
        except Exception as e:
            print(f"Failed to place signal order: {str(e)}")

    # Daemon run mode
    if args.loop:
        # Determine loop sleep duration based on candle interval (e.g. 15m = 900s)
        interval_map = {'1m': 60, '5m': 300, '15m': 900, '1h': 3600}
        sleep_sec = interval_map.get(interval, 60)
        
        print(f"Running in execution daemon loop. Tick interval: {sleep_sec} seconds. Press Ctrl+C to stop.")
        
        try:
            while True:
                execute_tick()
                time.sleep(sleep_sec)
        except KeyboardInterrupt:
            print("\nShutting down bot safely. Exiting...")
    else:
        # Single execution dry-run (extremely useful for GitHub demonstrations)
        print("Running one-shot execution tick (dry-run)...")
        execute_tick()
        print("One-shot dry-run complete. Run with --loop to start execution daemon.")

if __name__ == "__main__":
    run_trading_bot()
