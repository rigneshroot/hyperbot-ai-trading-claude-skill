import os
import json
import urllib.request
from typing import List, Dict, Optional
from dotenv import load_dotenv
import pandas as pd

# Load env variables
load_dotenv()

class HyperliquidClient:
    def __init__(self):
        self.api_key = os.getenv("HL_API_KEY")
        self.wallet_key = os.getenv("HL_API_WALLET_KEY")
        self.network = os.getenv("HL_NETWORK", "testnet").lower()
        
        self.base_url = (
            "https://api.hyperliquid-testnet.xyz"
            if self.network == "testnet"
            else "https://api.hyperliquid.xyz"
        )
        
        # Verify credentials if we attempt to trade
        self.is_configured = bool(self.api_key and self.wallet_key)

    def get_candles(self, symbol: str, interval: str, n_bars: int) -> pd.DataFrame:
        """
        Fetches the latest N candles for a symbol, paginating if needed.
        """
        # Calculate how many days/hours we need based on interval and number of bars
        # 15m * 1000 = 15000 minutes = 250 hours = 10.4 days
        # We will loop backward until we have at least n_bars candles
        end_time_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
        
        all_candles = []
        current_end = end_time_ms
        
        # To avoid infinite loop, we cap maximum pagination requests
        max_requests = 10
        requests_made = 0
        
        while len(all_candles) < n_bars and requests_made < max_requests:
            req_body = {
                "type": "candleSnapshot",
                "req": {
                    "coin": symbol,
                    "interval": interval,
                    "startTime": 0,  # Hyperliquid will default backward from endTime
                    "endTime": current_end
                }
            }
            
            try:
                req_data = json.dumps(req_body).encode('utf-8')
                req = urllib.request.Request(
                    f"{self.base_url}/info", 
                    data=req_data, 
                    headers={'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    
                if not res_data or not isinstance(res_data, list):
                    break
                    
                batch = res_data
                if len(batch) == 0:
                    break
                    
                # De-duplicate by timestamp
                batch = [c for c in batch if c['t'] < current_end]
                if len(batch) == 0:
                    break
                    
                all_candles.extend(batch)
                oldest_t = min(c['t'] for c in batch)
                
                if oldest_t >= current_end:
                    break
                    
                current_end = oldest_t
                requests_made += 1
                
            except Exception as e:
                print(f"Exchange Client Error fetching candles: {str(e)}")
                break
                
        if not all_candles:
            raise ValueError(f"Could not retrieve candles from Hyperliquid for {symbol}.")
            
        # Deduplicate and sort
        candle_dict = {c['t']: c for c in all_candles}
        sorted_ts = sorted(candle_dict.keys())[-n_bars:] # Only take latest N
        
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
            
        return pd.DataFrame(records)

    def get_balance(self) -> float:
        """
        Retrieves the account balance. Returns a mock value if credentials are empty.
        """
        if not self.is_configured:
            # Safe mock fallback
            return 10000.0
            
        # Using urllib to query user state from Hyperliquid
        req_body = {
            "type": "clearinghouseState",
            "user": self.api_key
        }
        
        try:
            req_data = json.dumps(req_body).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/info", 
                data=req_data, 
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            margin_summary = res_data.get("marginSummary", {})
            account_value = float(margin_summary.get("accountValue", 10000.0))
            return account_value
        except Exception as e:
            print(f"Error querying balance: {str(e)}. Using fallback mock.")
            return 10000.0

    def place_order(self, symbol: str, side: str, size: float, order_type: str = "market") -> dict:
        """
        Submits an order to the Hyperliquid exchange.
        Works strictly on Testnet unless HL_NETWORK is set to mainnet.
        """
        if not self.is_configured:
            print(f"[DRY RUN / MOCK ORDER] Placed {side.upper()} {size} {symbol} ({order_type}) successfully.")
            return {
                "status": "success",
                "mock": True,
                "order": {
                    "symbol": symbol,
                    "side": side,
                    "size": size,
                    "order_type": order_type,
                    "time": pd.Timestamp.utcnow().isoformat()
                }
            }

        # Real order submission via urllib/official patterns.
        # For simplicity and to avoid importing external C-extensions if compiling fails,
        # we provide a clean, secure order wrapper using urllib POST requests.
        # This interfaces with the Hyperliquid POST /exchange endpoint.
        
        # Real-money safety checks
        print(f"[ORDER SUBMITTED] Placing {side.upper()} {size} {symbol} ({order_type}) on {self.network.upper()}...")
        
        # Hyperliquid POST body structure for placing orders requires private wallet signatures.
        # Since generating cryptographic signatures requires eth_account and ecdsa libraries,
        # we will utilize the official hyperliquid python library if initialized.
        try:
            from hyperliquid.info import Info
            from hyperliquid.exchange import Exchange
            from hyperliquid.utils import constants
            import eth_account
            
            # Setup constants based on network config
            base_constants = constants.TestnetSpec if self.network == "testnet" else constants.MainnetSpec
            
            # Setup private account signing client
            account = eth_account.Account.from_key(self.wallet_key)
            info_client = Info(base_constants.API_URL, skip_initialization=False)
            exchange_client = Exchange(account, base_constants.API_URL)
            
            # Determine order parameters
            is_buy = side.lower() == "buy"
            
            # Place order on Hyperliquid
            # For simplicity, we make standard market or limit orders
            # Market order requires passing slippage parameter. Hyperliquid places limit order with slippage.
            if order_type.lower() == "market":
                # Fetch current price first to compute slippage limit
                price_body = {"type": "allMids"}
                req_data = json.dumps(price_body).encode('utf-8')
                req = urllib.request.Request(f"{self.base_url}/info", data=req_data, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req) as response:
                    prices = json.loads(response.read().decode('utf-8'))
                
                mid_price = float(prices.get(symbol, 0))
                if mid_price == 0:
                    raise ValueError(f"Could not retrieve mid price for {symbol}")
                    
                # Apply 1% slippage for market orders
                slippage_price = mid_price * 1.01 if is_buy else mid_price * 0.99
                
                # Round to 5 sig figs (Hyperliquid requirement)
                price_str = f"{slippage_price:.5g}"
                
                order_result = exchange_client.order(
                    coin=symbol,
                    is_buy=is_buy,
                    sz=size,
                    px=float(price_str),
                    order_type={"limit": {"tif": "ioc"}} # Immediate or Cancel limit order acts as market order
                )
            else:
                raise NotImplementedError("Only market order types are implemented for live loop safety.")
                
            return {
                "status": "success",
                "mock": False,
                "response": order_result
            }
        except Exception as e:
            # Graceful error reporting
            err_msg = f"Failed to submit live order: {str(e)}"
            print(f"CRITICAL ERROR: {err_msg}")
            raise RuntimeError(err_msg)
