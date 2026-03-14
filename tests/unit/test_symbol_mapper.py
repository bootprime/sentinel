"""
Unit tests for Symbol Mapper
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from core.symbol_mapper import SymbolMapper


class TestSymbolMapper:
    """Test symbol mapping for all brokers"""
    
    def setup_method(self):
        """Mock internal logger/audit for all tests in this class"""
        # patch the module-level logger/audit in core.symbol_mapper
        self.logger_patcher = patch('core.symbol_mapper.log_module.logger')
        self.audit_patcher = patch('core.symbol_mapper.audit_module.audit')
        self.mock_logger = self.logger_patcher.start()
        self.mock_audit = self.audit_patcher.start()

    def teardown_method(self):
        self.logger_patcher.stop()
        self.audit_patcher.stop()

    def test_kite_format(self):
        """Test Kite symbol format conversion"""
        expiry = datetime(2026, 2, 20)
        symbol = SymbolMapper.to_kite("NIFTY", 24500, "CE", expiry)
        assert symbol == "NIFTY26FEB24500CE"
    
    def test_kite_format_banknifty(self):
        """Test Kite format for BANKNIFTY"""
        expiry = datetime(2026, 3, 15)
        symbol = SymbolMapper.to_kite("BANKNIFTY", 50000, "PE", expiry)
        assert symbol == "BANKNIFTY26MAR50000PE"
    
    def test_dhan_format(self):
        """Test Dhan symbol format conversion"""
        expiry = datetime(2026, 2, 20)
        symbol = SymbolMapper.to_dhan("NIFTY", 24500, "CE", expiry)
        assert symbol == "NIFTY 20 FEB 2026 CE 24500"
    
    def test_dhan_format_single_digit_day(self):
        """Test Dhan format with single-digit day"""
        expiry = datetime(2026, 3, 5)
        symbol = SymbolMapper.to_dhan("NIFTY", 24000, "PE", expiry)
        assert symbol == "NIFTY 05 MAR 2026 PE 24000"
    
    def test_delta_product_id(self):
        """Test Delta product ID lookup"""
        # Ensure map has default values
        assert SymbolMapper.to_delta("BTCUSD") == 27
        assert SymbolMapper.to_delta("ETHUSD") == 28
    
    def test_delta_unknown_symbol(self):
        """Test Delta with unknown symbol"""
        product_id = SymbolMapper.to_delta("UNKNOWN")
        assert product_id is None
    
    def test_get_broker_symbol_kite(self):
        """Test get_broker_symbol for Kite"""
        expiry = datetime(2026, 2, 20)
        symbol = SymbolMapper.get_broker_symbol(
            broker="KITE",
            base="NIFTY",
            strike=24500,
            opt_type="CE",
            expiry=expiry
        )
        assert symbol == "NIFTY26FEB24500CE"
    
    def test_get_broker_symbol_zerodha(self):
        """Test get_broker_symbol for ZERODHA (alias for KITE)"""
        expiry = datetime(2026, 2, 20)
        symbol = SymbolMapper.get_broker_symbol(
            broker="ZERODHA",
            base="NIFTY",
            strike=24500,
            opt_type="CE",
            expiry=expiry
        )
        assert symbol == "NIFTY26FEB24500CE"
    
    def test_get_broker_symbol_dhan(self):
        """Test get_broker_symbol for Dhan"""
        expiry = datetime(2026, 2, 20)
        symbol = SymbolMapper.get_broker_symbol(
            broker="DHAN",
            base="NIFTY",
            strike=24500,
            opt_type="CE",
            expiry=expiry
        )
        assert symbol == "NIFTY 20 FEB 2026 CE 24500"
    
    def test_get_broker_symbol_delta(self):
        """Test get_broker_symbol for Delta"""
        symbol = SymbolMapper.get_broker_symbol(
            broker="DELTA",
            symbol="BTCUSD"
        )
        assert symbol == "27"
    
    def test_get_broker_symbol_missing_params(self):
        """Test error handling for missing parameters"""
        # Kite without expiry
        symbol = SymbolMapper.get_broker_symbol(
            broker="KITE",
            base="NIFTY",
            strike=24500,
            opt_type="CE"
        )
        assert symbol is None
        
        # Delta without symbol
        symbol = SymbolMapper.get_broker_symbol(
            broker="DELTA"
        )
        assert symbol is None
    
    def test_get_broker_symbol_unknown_broker(self):
        """Test unknown broker handling"""
        expiry = datetime(2026, 2, 20)
        symbol = SymbolMapper.get_broker_symbol(
            broker="UNKNOWN",
            base="NIFTY",
            strike=24500,
            opt_type="CE",
            expiry=expiry
        )
        assert symbol is None
        # Verify audit error was called
        # self.mock_audit.error.assert_called()
    
    def test_add_delta_product(self):
        """Test adding Delta product dynamically"""
        # Patching logger/audit locally handles this method's side effects
        SymbolMapper.add_delta_product("TESTUSD", 999)
        
        product_id = SymbolMapper.to_delta("TESTUSD")
        assert product_id == 999
    
    def test_get_delta_products(self):
        """Test getting all Delta products"""
        products = SymbolMapper.get_delta_products()
        
        assert isinstance(products, dict)
        assert "BTCUSD" in products
        assert products["BTCUSD"] == 27
    
    def test_case_insensitive_delta(self):
        """Test Delta symbol lookup is case-insensitive"""
        product_id1 = SymbolMapper.to_delta("btcusd")
        product_id2 = SymbolMapper.to_delta("BTCUSD")
        product_id3 = SymbolMapper.to_delta("BtcUsd")
        
        assert product_id1 == product_id2 == product_id3 == 27
