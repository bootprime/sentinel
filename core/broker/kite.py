from typing import List, Dict, Any
from kiteconnect import KiteConnect
from core.broker.base import IBroker
from core.logger import logger, LogCategory
from core.audit import audit
from core.contract import SignalPayload
import logging

class KiteBroker(IBroker):
    """
    Zerodha Kite Implementation for Sentinel.
    Requires: api_key, access_token (Manual Login or Auto)
    """
    def __init__(self):
        self.kite = None
        self.api_key = None
        self.access_token = None

    def authenticate(self, credentials: dict) -> bool:
        """
        Expects: {"api_key": "...", "access_token": "..."}
        """
        try:
            self.api_key = credentials.get("api_key")
            self.access_token = credentials.get("access_token")
            
            if not self.api_key or not self.access_token:
                logger.audit(LogCategory.SECURITY, "Kite Authentication Failed: Missing API Key or Access Token")
                return False

            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            
            # Verify connectivity
            profile = self.kite.profile()
            logger.system(LogCategory.SECURITY, f"Kite Connected: {profile.get('user_id')} ({profile.get('user_name')})")
            return True
        except Exception as e:
            logger.audit(LogCategory.SECURITY, f"Kite Connection Error: {str(e)}")
            return False

    def place_order(self, order_params: dict) -> dict:
        """
        Translates Sentinel Generic Order -> Kite Order
        params: { "symbol": "NIFTY24JAN...", "qty": 50, "type": "BUY/SELL", "order_type": "MARKET/SL", "trigger_price": ... }
        """
        try:
            tradingsymbol = order_params.get("symbol")
            transaction_type = self.kite.TRANSACTION_TYPE_BUY if order_params.get("type") == "BUY" else self.kite.TRANSACTION_TYPE_SELL
            quantity = int(order_params.get("qty", 0))
            
            # Default to MARKET unless SL specified
            order_type = self.kite.ORDER_TYPE_MARKET
            trigger_price = None
            price = None # For MARKET, price is 0/None

            if order_params.get("order_type") == "SL":
                order_type = self.kite.ORDER_TYPE_SL
                trigger_price = float(order_params.get("trigger_price"))
                # SL-M is often safer for guaranteed exit, but SL-L is standard.
                # Let's use SL-M (Stoploss Market) if possible to ensure exit? 
                # Kite API has ORDER_TYPE_SLM.
                # Configurable? For now, risk engine usually asks for 'SL' which implies trigger exection.
                # Let's use SL-M for safety if it's a STOP LOSS.
                order_type = self.kite.ORDER_TYPE_SLM
            
            exchange = "NFO" # Intraday Options are usually NFO
            
            # Check if symbol is valid (basic check)
            if not tradingsymbol:
                raise ValueError("Symbol is missing")

            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=self.kite.PRODUCT_MIS, # Intraday
                order_type=order_type,
                price=price,
                trigger_price=trigger_price,
                tag="SENTINEL_V1"
            )
            
            logger.system(LogCategory.EXECUTION, f"Kite Order Placed: {order_id}")
            return {"status": "success", "order_id": order_id}

        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Kite Place Order Failed: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def get_order_status(self, order_id: str) -> dict:
        try:
            history = self.kite.order_history(order_id)
            if not history:
                return {"status": "UNKNOWN"}
            
            # Get latest status
            latest = history[-1]
            status = latest.get("status") # COMPLETE, REJECTED, CANCELLED, OPEN
            
            fill_price = 0.0
            fill_qty = 0
            
            if status == "COMPLETE":
                fill_price = latest.get("average_price", 0.0)
                fill_qty = latest.get("filled_quantity", 0)
            elif status == "OPEN" and latest.get("filled_quantity", 0) > 0:
                status = "PARTIAL"
                fill_price = latest.get("average_price", 0.0)
                fill_qty = latest.get("filled_quantity", 0)

            return {
                "status": status,
                "fill_price": fill_price,
                "fill_qty": fill_qty,
                "details": latest
            }
        except Exception as e:
            audit.error(f"Kite Status Check Failed: {str(e)}")
            # Don't throw, return pending to keep polling loop alive if transient error
            return {"status": "PENDING", "error": str(e)}

    def get_positions(self) -> list:
        try:
            positions = self.kite.positions()
            net = positions.get("net", [])
            # Convert to Sentinel format if needed
            return net
        except Exception as e:
            audit.error(f"Kite Values Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            self.kite.cancel_order(
                variety=self.kite.VARIETY_REGULAR,
                order_id=order_id
            )
            return True
        except Exception as e:
            audit.error(f"Kite Cancel Error: {e}")
            return False

    def get_ltp(self, symbol: str) -> float:
        """
        Fetches LTP using Kite quote API.
        Expected format: {'NSE:NIFTY 50': {'last_price': 21000.5}}
        """
        try:
            # We assume NFO for options, NSE for index
            instrument = f"NFO:{symbol}" if "NIFTY" in symbol and any(c.isdigit() for c in symbol) else f"NSE:{symbol}"
            quote = self.kite.quote(instrument)
            return quote.get(instrument, {}).get("last_price", 0.0)
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Kite LTP Fetch Failed for {symbol}: {e}")
            return 0.0

    def get_open_orders(self) -> List[Dict[str, Any]]:
        """
        Fetches all orders and filters for pending statuses.
        """
        try:
            all_orders = self.kite.orders()
            # Kite pending statuses: OPEN, MODIFY PENDING, TRIGGER PENDING
            pending_statuses = ["OPEN", "MODIFY PENDING", "TRIGGER PENDING"]
            return [o for o in all_orders if o.get("status") in pending_statuses]
        except Exception as e:
            audit.error(f"Kite Open Orders Fetch Failed: {e}")
            return []

    def flatten_position(self, symbol: str) -> bool:
        """
        Emergency square off for a specific symbol.
        Finds open position and sends opposite market order.
        """
        try:
            positions = self.get_positions()
            for p in positions:
                if p["tradingsymbol"] == symbol and p["product"] == "MIS":
                    qty = p["quantity"]
                    if qty != 0:
                        audit.warning(f"Flattening {symbol}, Qty: {qty}")
                        direction = "SELL" if qty > 0 else "BUY"
                        self.place_order({
                            "symbol": symbol,
                            "qty": abs(qty),
                            "type": direction,
                            "order_type": "MARKET"
                        })
            return True
        except Exception as e:
            audit.critical(f"Kite Flatten Error: {e}")
            return False
