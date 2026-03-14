"""
Delta Exchange Broker Implementation for Sentinel
Supports derivatives trading on Delta Exchange (India's leading crypto derivatives exchange)
"""

from typing import List, Dict, Any, Optional
from core.broker.base import IBroker
from core.logger import logger, LogCategory
from core.audit import audit
import requests
import hmac
import hashlib
import time
from datetime import datetime


class DeltaBroker(IBroker):
    """
    Delta Exchange Implementation for Sentinel.
    Requires: api_key, api_secret
    
    Delta Exchange API Documentation:
    https://docs.delta.exchange/
    """
    
    # API Endpoints
    BASE_URL = "https://api.delta.exchange"
    TESTNET_URL = "https://testnet-api.delta.exchange"
    
    def __init__(self, testnet: bool = False):
        self.api_key = None
        self.api_secret = None
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.session = requests.Session()
        
    def _generate_signature(self, method: str, endpoint: str, payload: str = "") -> str:
        """
        Generate HMAC SHA256 signature for Delta Exchange API
        """
        timestamp = str(int(time.time()))
        signature_data = method + timestamp + endpoint + payload
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    def _make_request(self, method: str, endpoint: str, payload: dict = None) -> dict:
        """
        Make authenticated request to Delta Exchange API
        """
        try:
            url = f"{self.base_url}{endpoint}"
            payload_str = "" if payload is None else str(payload)
            
            signature, timestamp = self._generate_signature(method, endpoint, payload_str)
            
            headers = {
                "api-key": self.api_key,
                "signature": signature,
                "timestamp": timestamp,
                "Content-Type": "application/json"
            }
            
            if method == "GET":
                response = self.session.get(url, headers=headers)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=payload)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            audit.error(f"Delta API Request Failed: {e}")
            return {"success": False, "error": str(e)}
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with Delta Exchange using API key and secret.
        Expects: {"api_key": "...", "api_secret": "..."}
        """
        try:
            self.api_key = credentials.get("api_key")
            self.api_secret = credentials.get("api_secret")
            
            if not self.api_key or not self.api_secret:
                logger.audit(LogCategory.SECURITY, "Delta Authentication Failed: Missing API Key or Secret")
                return False
            
            # Verify credentials by fetching profile
            response = self._make_request("GET", "/v2/profile")
            
            if response.get("success"):
                profile = response.get("result", {})
                user_id = profile.get("user_id")
                email = profile.get("email", "N/A")
                logger.system(LogCategory.SECURITY, f"Delta Connected: {user_id} ({email})")
                return True
            else:
                logger.audit(LogCategory.SECURITY, f"Delta Profile Fetch Failed: {response.get('error')}")
                return False
                
        except Exception as e:
            logger.audit(LogCategory.SECURITY, f"Delta Connection Error: {str(e)}")
            return False
    
    def place_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place order on Delta Exchange.
        Translates Sentinel Generic Order → Delta Order
        
        Delta Order Parameters:
        - product_id: Contract ID (e.g., 27 for BTCUSD)
        - size: Order quantity
        - side: "buy" or "sell"
        - order_type: "market_order" or "limit_order"
        - limit_price: Required for limit orders
        - stop_price: For stop orders
        """
        try:
            # Map Sentinel params to Delta format
            side = "buy" if order_params.get("type") == "BUY" else "sell"
            size = int(order_params.get("qty", 0))
            
            # Get product_id from symbol mapping
            # For now, we'll need to implement symbol → product_id mapping
            product_id = self._get_product_id(order_params.get("symbol"))
            
            if not product_id:
                raise ValueError(f"Invalid symbol: {order_params.get('symbol')}")
            
            # Build order payload
            order_payload = {
                "product_id": product_id,
                "size": size,
                "side": side,
                "order_type": "market_order",  # Default to market
                "time_in_force": "ioc"  # Immediate or cancel
            }
            
            # Handle stop loss orders
            if order_params.get("order_type") == "SL":
                order_payload["order_type"] = "stop_market_order"
                order_payload["stop_price"] = str(order_params.get("trigger_price"))
            
            # Place order
            response = self._make_request("POST", "/v2/orders", order_payload)
            
            if response.get("success"):
                order_data = response.get("result", {})
                order_id = order_data.get("id")
                logger.system(LogCategory.EXECUTION, f"Delta Order Placed: {order_id}")
                return {"status": "success", "order_id": str(order_id)}
            else:
                error_msg = response.get("error", {}).get("message", "Unknown error")
                logger.debug(LogCategory.EXECUTION, f"Delta Order Failed: {error_msg}")
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Delta Place Order Exception: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status from Delta Exchange.
        
        Delta Order States:
        - open: Order is open
        - pending: Order is pending
        - closed: Order is filled
        - cancelled: Order is cancelled
        """
        try:
            response = self._make_request("GET", f"/v2/orders/{order_id}")
            
            if not response.get("success"):
                return {"status": "UNKNOWN"}
            
            order = response.get("result", {})
            state = order.get("state")
            
            # Map Delta states to Sentinel states
            status_map = {
                "closed": "COMPLETE",
                "cancelled": "CANCELLED",
                "open": "OPEN",
                "pending": "OPEN"
            }
            
            sentinel_status = status_map.get(state, "UNKNOWN")
            
            fill_price = 0.0
            fill_qty = 0
            
            if sentinel_status == "COMPLETE":
                fill_price = float(order.get("average_fill_price", 0.0))
                fill_qty = int(order.get("size", 0))
            elif sentinel_status == "OPEN" and int(order.get("filled_size", 0)) > 0:
                sentinel_status = "PARTIAL"
                fill_price = float(order.get("average_fill_price", 0.0))
                fill_qty = int(order.get("filled_size", 0))
            
            return {
                "status": sentinel_status,
                "fill_price": fill_price,
                "fill_qty": fill_qty,
                "details": order
            }
            
        except Exception as e:
            audit.error(f"Delta Status Check Failed: {str(e)}")
            return {"status": "PENDING", "error": str(e)}
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Fetch open positions from Delta Exchange.
        """
        try:
            response = self._make_request("GET", "/v2/positions")
            
            if response.get("success"):
                return response.get("result", [])
            return []
            
        except Exception as e:
            audit.error(f"Delta Positions Error: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order on Delta Exchange.
        """
        try:
            response = self._make_request("DELETE", f"/v2/orders/{order_id}")
            success = response.get("success", False)
            
            if success:
                logger.system(LogCategory.EXECUTION, f"Delta Order Cancelled: {order_id}")
            else:
                logger.debug(LogCategory.EXECUTION, f"Delta Cancel Failed: {response.get('error')}")
            
            return success
            
        except Exception as e:
            audit.error(f"Delta Cancel Error: {e}")
            return False
    
    def get_ltp(self, symbol: str) -> float:
        """
        Get Last Traded Price for a symbol from Delta Exchange.
        Uses ticker API endpoint.
        """
        try:
            product_id = self._get_product_id(symbol)
            if not product_id:
                return 0.0
            
            response = self._make_request("GET", f"/v2/tickers/{product_id}")
            
            if response.get("success"):
                ticker = response.get("result", {})
                return float(ticker.get("close", 0.0))
            return 0.0
            
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Delta LTP Fetch Failed for {symbol}: {e}")
            return 0.0
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all open orders from Delta Exchange.
        """
        try:
            response = self._make_request("GET", "/v2/orders")
            
            if response.get("success"):
                all_orders = response.get("result", [])
                # Filter for open/pending orders
                return [o for o in all_orders if o.get("state") in ["open", "pending"]]
            return []
            
        except Exception as e:
            audit.error(f"Delta Open Orders Fetch Failed: {e}")
            return []
    
    def flatten_position(self, symbol: str) -> bool:
        """
        Emergency square off for a specific symbol.
        Closes the position by placing an opposite market order.
        """
        try:
            positions = self.get_positions()
            product_id = self._get_product_id(symbol)
            
            for position in positions:
                if position.get("product_id") == product_id:
                    size = int(position.get("size", 0))
                    
                    if size != 0:
                        audit.warning(f"Delta Flattening {symbol}, Size: {size}")
                        
                        # Opposite side to close position
                        side = "sell" if size > 0 else "buy"
                        
                        self.place_order({
                            "symbol": symbol,
                            "qty": abs(size),
                            "type": "SELL" if size > 0 else "BUY",
                            "order_type": "MARKET"
                        })
            
            return True
            
        except Exception as e:
            audit.critical(f"Delta Flatten Error: {e}")
            return False
    
    def _get_product_id(self, symbol: str) -> Optional[int]:
        """
        Map Sentinel symbol to Delta Exchange product_id using symbol mapper.
        
        Args:
            symbol: Crypto symbol (e.g., "BTCUSD")
            
        Returns:
            Product ID or None if not found
        """
        from core.symbol_mapper import symbol_mapper
        
        product_id = symbol_mapper.to_delta(symbol)
        
        if product_id is None:
            audit.warning(f"Delta product ID not found for symbol: {symbol}")
        
        return product_id
    
    def cancel_all(self) -> bool:
        """
        Cancel all open orders (emergency function).
        """
        try:
            response = self._make_request("DELETE", "/v2/orders/all")
            return response.get("success", False)
        except Exception as e:
            audit.critical(f"Delta Cancel All Failed: {e}")
            return False
