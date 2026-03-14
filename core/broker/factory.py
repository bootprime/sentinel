from .base import IBroker
from .upstox import UpstoxBroker
from .multi import DhanBroker, ZerodhaBroker
from typing import Dict, Type

class BrokerFactory:
    """
    Manages and creates broker instances.
    Supports dynamic switching between Upstox, Dhan, Zerodha, and Delta Exchange.
    """
    
    _brokers: Dict[str, Type[IBroker]] = {
        "UPSTOX": UpstoxBroker,
        "DHAN": DhanBroker,
        "ZERODHA": ZerodhaBroker
    }
    
    @staticmethod # Changed from @classmethod
    def get_broker(broker_name: str, testnet: bool = False) -> IBroker: # Changed parameter name and return type
        if broker_name == "ZERODHA" or broker_name == "KITE":
            from .kite import KiteBroker
            return KiteBroker()
        
        if broker_name == "DHAN":
            from .dhan import DhanBroker
            return DhanBroker()
        
        if broker_name == "DELTA":
            from .delta import DeltaBroker
            return DeltaBroker(testnet=testnet)
        
        # Fallback
        from .null import NullBroker
        return NullBroker() # Corrected typo: removed _cls()

