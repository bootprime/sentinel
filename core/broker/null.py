from typing import List, Dict, Any
from .base import IBroker
from core.logger import logger, LogCategory

class NullBroker(IBroker):
    """
    Mock broker for testing and Paper-only mode without API keys.
    """
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        return True

    def get_ltp(self, symbol: str) -> float:
        # Return a mock price
        return 21500.5

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {
            "status": "COMPLETE",
            "fill_price": 21500.5,
            "fill_qty": 50
        }

    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        logger.system(LogCategory.EXECUTION, f"MOCKED ORDER PLACED: {order_details.get('symbol')}")
        return {"status": "success", "order_id": "MOCK-ORD-123"}

    def flatten_position(self, symbol: str) -> Dict[str, Any]:
        return {"status": "success"}

    def get_open_orders(self) -> List[Dict[str, Any]]:
        return []

    def get_positions(self) -> Dict[str, Any]:
        return {"net": []}
