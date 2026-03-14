"""
Symbol Mapping Service
Converts generic symbols to broker-specific formats for multi-broker compatibility.

Supports:
- Zerodha (Kite): NIFTY26FEB24500CE
- Dhan: NIFTY 20 FEB 2026 CE 24500
- Delta Exchange: Product ID lookup (for crypto)
"""

from typing import Optional
from datetime import datetime
import json
import os
import core.logger as log_module
import core.audit as audit_module


class SymbolMapper:
    """
    Multi-broker symbol format converter.
    
    Example conversions:
    Generic: base="NIFTY", strike=24500, type="CE", expiry=2026-02-20
    
    → Kite:  "NIFTY26FEB24500CE"
    → Dhan:  "NIFTY 20 FEB 2026 CE 24500"
    → Delta: Product ID (requires mapping table)
    """
    
    # Delta product ID cache (loaded from config)
    DELTA_PRODUCT_MAP = {
        "BTCUSD": 27,
        "ETHUSD": 28,
        "SOLUSD": 139,
        "BNBUSD": 45,
        "ADAUSD": 78,
    }
    
    @staticmethod
    def to_kite(base: str, strike: int, opt_type: str, expiry: datetime) -> str:
        """
        Convert to Kite format: NIFTY26FEB24500CE
        
        Args:
            base: Index symbol (e.g., "NIFTY", "BANKNIFTY")
            strike: Strike price (e.g., 24500)
            opt_type: "CE" or "PE"
            expiry: Expiry date
            
        Returns:
            Kite-formatted symbol string
        """
        year = expiry.strftime("%y")
        month = expiry.strftime("%b").upper()
        return f"{base}{year}{month}{strike}{opt_type}"
    
    @staticmethod
    def to_dhan(base: str, strike: int, opt_type: str, expiry: datetime) -> str:
        """
        Convert to Dhan format: NIFTY 20 FEB 2026 CE 24500
        
        Args:
            base: Index symbol
            strike: Strike price
            opt_type: "CE" or "PE"
            expiry: Expiry date
            
        Returns:
            Dhan-formatted symbol string
        """
        day = expiry.strftime("%d")
        month = expiry.strftime("%b").upper()
        year = expiry.strftime("%Y")
        return f"{base} {day} {month} {year} {opt_type} {strike}"
    
    @staticmethod
    def to_delta(symbol: str) -> Optional[int]:
        """
        Convert to Delta Exchange product ID.
        
        For crypto symbols like BTCUSD, ETHUSD.
        For options, this would require API lookup or extended mapping.
        
        Args:
            symbol: Crypto symbol (e.g., "BTCUSD")
            
        Returns:
            Product ID or None if not found
        """
        return SymbolMapper.DELTA_PRODUCT_MAP.get(symbol.upper())
    
    @staticmethod
    def get_broker_symbol(
        broker: str,
        base: str,
        strike: Optional[int] = None,
        opt_type: Optional[str] = None,
        expiry: Optional[datetime] = None,
        symbol: Optional[str] = None
    ) -> Optional[str]:
        """
        Get broker-specific symbol format.
        
        For equity derivatives (Kite/Dhan): Requires base, strike, opt_type, expiry
        For crypto (Delta): Requires symbol
        
        Args:
            broker: Broker name ("KITE", "DHAN", "DELTA")
            base: Index symbol (for options)
            strike: Strike price (for options)
            opt_type: "CE" or "PE" (for options)
            expiry: Expiry date (for options)
            symbol: Direct symbol (for crypto)
            
        Returns:
            Broker-specific symbol string or None
        """
        broker = broker.upper()
        
        try:
            if broker in ["KITE", "ZERODHA"]:
                if not all([base, strike, opt_type, expiry]):
                    raise ValueError("Kite requires: base, strike, opt_type, expiry")
                return SymbolMapper.to_kite(base, strike, opt_type, expiry)
            
            elif broker == "DHAN":
                if not all([base, strike, opt_type, expiry]):
                    raise ValueError("Dhan requires: base, strike, opt_type, expiry")
                return SymbolMapper.to_dhan(base, strike, opt_type, expiry)
            
            elif broker == "DELTA":
                if not symbol:
                    raise ValueError("Delta requires: symbol")
                product_id = SymbolMapper.to_delta(symbol)
                if product_id is None:
                    log_module.logger.debug(log_module.LogCategory.EXECUTION, f"Delta product ID not found for {symbol}")
                    return None
                return str(product_id)
            
            else:
                audit_module.audit.error(f"Unknown broker for symbol mapping: {broker}")
                return None
                
        except Exception as e:
            audit_module.audit.error(f"Symbol mapping error for {broker}: {e}")
            return None
    
    @staticmethod
    def load_delta_products(file_path: str = "data/delta_products.json"):
        """
        Load Delta product mappings from file.
        This allows dynamic updates without code changes.
        
        File format:
        {
            "BTCUSD": 27,
            "ETHUSD": 28,
            ...
        }
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    products = json.load(f)
                    SymbolMapper.DELTA_PRODUCT_MAP.update(products)
                    log_module.logger.system(log_module.LogCategory.SYSTEM, f"Loaded {len(products)} Delta products from {file_path}")
        except Exception as e:
            audit_module.audit.warning(f"Failed to load Delta products: {e}")
    
    @staticmethod
    def add_delta_product(symbol: str, product_id: int):
        """
        Add a new Delta product mapping dynamically.
        """
        SymbolMapper.DELTA_PRODUCT_MAP[symbol.upper()] = product_id
        log_module.logger.system(log_module.LogCategory.SYSTEM, f"Added Delta product: {symbol} → {product_id}")
    
    @staticmethod
    def get_delta_products() -> dict:
        """
        Get all Delta product mappings.
        """
        return SymbolMapper.DELTA_PRODUCT_MAP.copy()


# Global instance
symbol_mapper = SymbolMapper()
