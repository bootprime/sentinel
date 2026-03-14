from typing import List, Dict, Any
from dhanhq import dhanhq
from core.broker.base import IBroker
from core.logger import logger, LogCategory
from core.audit import audit
import time

class DhanBroker(IBroker):
    """
    DhanHQ Implementation for Sentinel.
    Requires: client_id, access_token
    """
    def __init__(self):
        self.dhan = None
        self.client_id = None
        self.access_token = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Expects: {"client_id": "...", "access_token": "..."}
        """
        try:
            self.client_id = credentials.get("client_id")
            self.access_token = credentials.get("access_token")
            
            if not self.client_id or not self.access_token:
                logger.audit(LogCategory.SECURITY, "Dhan Authentication Failed: Missing Client ID or Access Token")
                return False

            self.dhan = dhanhq(client_id=self.client_id, access_token=self.access_token)
            
            # Verify connectivity by fetching profile
            profile = self.dhan.get_profile_adept()
            if profile.get("status") == "success":
                data = profile.get("data", {})
                logger.system(LogCategory.SECURITY, f"Dhan Connected: {data.get('client_id')} ({data.get('name')})")
                return True
            else:
                logger.audit(LogCategory.SECURITY, f"Dhan Profile Fetch Failed: {profile.get('remarks')}")
                return False
        except Exception as e:
            logger.audit(LogCategory.SECURITY, f"Dhan Connection Error: {str(e)}")
            return False

    def get_ltp(self, symbol: str) -> float:
        """
        Fetches LTP using Dhan Quote API.
        """
        try:
            # Dhan requires instrument mapping. For now, we use a simplified mock or try to fetch.
            # Real implementation would need security_id lookup.
            # Placeholder for mapping logic
            return 0.0 
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Dhan LTP Fetch Failed for {symbol}: {e}")
            return 0.0

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            response = self.dhan.get_order_by_id(order_id)
            if response.get("status") != "success":
                return {"status": "UNKNOWN"}
            
            data = response.get("data", {})
            order_status = data.get("orderStatus") # TRADED, REJECTED, CANCELLED, TRANSIT
            
            fill_price = 0.0
            fill_qty = 0
            
            # Mapping Dhan Statuses to Sentinel Statuses
            status_map = {
                "TRADED": "COMPLETE",
                "REJECTED": "REJECTED",
                "CANCELLED": "CANCELLED",
                "PENDING": "OPEN"
            }
            
            sentinel_status = status_map.get(order_status, "OPEN")
            
            if sentinel_status == "COMPLETE":
                fill_price = float(data.get("avgPrice", 0.0))
                fill_qty = int(data.get("tradedQuantity", 0))
            elif sentinel_status == "OPEN" and int(data.get("tradedQuantity", 0)) > 0:
                sentinel_status = "PARTIAL"
                fill_price = float(data.get("avgPrice", 0.0))
                fill_qty = int(data.get("tradedQuantity", 0))

            return {
                "status": sentinel_status,
                "fill_price": fill_price,
                "fill_qty": fill_qty,
                "details": data
            }
        except Exception as e:
            audit.error(f"Dhan Status Check Failed: {str(e)}")
            return {"status": "PENDING", "error": str(e)}

    def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sentinel Generic -> Dhan Order
        """
        try:
            # Dhan required fields: tag, transaction_type, exchange_segment, product_type, order_type, validity, trading_symbol, quantity
            # We assume NFO for options
            
            transaction_type = self.dhan.BUY if order_params.get("type") == "BUY" else self.dhan.SELL
            
            order_data = {
                "tag": "SENTINEL_V1",
                "transaction_type": transaction_type,
                "exchange_segment": self.dhan.NSE_FNO,
                "product_type": self.dhan.INTRA,
                "order_type": self.dhan.MARKET,
                "validity": self.dhan.DAY,
                "trading_symbol": order_params.get("symbol"),
                "quantity": int(order_params.get("qty", 0)),
                "price": 0,
                "trigger_price": 0
            }

            if order_params.get("order_type") == "SL":
                order_data["order_type"] = self.dhan.STOP_LOSS_MARKET
                order_data["trigger_price"] = float(order_params.get("trigger_price"))

            response = self.dhan.place_order(**order_data)
            
            if response.get("status") == "success":
                order_id = response.get("data", {}).get("orderId")
                logger.system(LogCategory.EXECUTION, f"Dhan Order Placed: {order_id}")
                return {"status": "success", "order_id": order_id}
            else:
                msg = response.get("remarks", "Unknown Error")
                return {"status": "error", "message": msg}

        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Dhan Place Order Failed: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def get_positions(self) -> list:
        try:
            response = self.dhan.get_positions()
            if response.get("status") == "success":
                return response.get("data", [])
            return []
        except Exception as e:
            audit.error(f"Dhan Positions Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            response = self.dhan.cancel_order(order_id)
            return response.get("status") == "success"
        except Exception as e:
            audit.error(f"Dhan Cancel Error: {e}")
            return False

    def flatten_position(self, symbol: str) -> bool:
        try:
            positions = self.get_positions()
            for p in positions:
                if p["tradingSymbol"] == symbol and p["positionType"] == "OPEN":
                    qty = int(p["netQty"])
                    if qty != 0:
                        audit.warning(f"Dhan Flattening {symbol}, Qty: {qty}")
                        direction = "SELL" if qty > 0 else "BUY"
                        self.place_order({
                            "symbol": symbol,
                            "qty": abs(qty),
                            "type": direction,
                            "order_type": "MARKET"
                        })
            return True
        except Exception as e:
            audit.critical(f"Dhan Flatten Error: {e}")
            return False

    def get_open_orders(self) -> List[Dict[str, Any]]:
        try:
            response = self.dhan.get_order_list()
            if response.get("status") == "success":
                all_orders = response.get("data", [])
                pending_statuses = ["PENDING"] # Dhan pending status
                return [o for o in all_orders if o.get("orderStatus") in pending_statuses]
            return []
        except Exception as e:
            audit.error(f"Dhan Open Orders Fetch Failed: {e}")
            return []
