from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IBroker(ABC):
    """
    Abstract Interface for Broker Compatibility (Upstox, Dhan, Zerodha).
    Handles both Trade Execution and Market Data.
    """
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticates with the broker API."""
        pass
    
    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        """Fetches Last Traded Price for a specific instrument."""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Polls broker for current order status.
        Expected return: {"status": "COMPLETE/PENDING/REJECTED", "fill_price": float, "fill_qty": int}
        """
        pass
    
    @abstractmethod
    def place_order(self, order_details: Dict[str, Any]) -> Dict[str, Any]:
        """Places an order with the broker."""
        pass
    
    @abstractmethod
    def flatten_position(self, symbol: str) -> Dict[str, Any]:
        """Emergency: Closes all open quantities for a symbol at Market."""
        pass

    @abstractmethod
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Retrieves currently active/pending orders."""
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, Any]:
        """Retrieves active positions."""
        pass
