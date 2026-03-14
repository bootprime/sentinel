"""
Unit tests for Market Data Manager
"""

import pytest
import asyncio
from core.market_data import MarketDataManager


class TestMarketDataManager:
    """Test market data manager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create market data manager instance"""
        return MarketDataManager()
    
    def test_init(self, manager):
        """Test initialization"""
        assert manager.ltp_cache == {}
        assert manager.subscriptions == set()
        assert manager.broker_streams == {}
        assert manager.running == False
    
    def test_get_ltp_empty_cache(self, manager):
        """Test get_ltp with empty cache"""
        ltp = manager.get_ltp("BTCUSD")
        assert ltp is None
    
    def test_get_ltp_with_cache(self, manager):
        """Test get_ltp with cached data"""
        from datetime import datetime
        
        manager.ltp_cache["BTCUSD"] = {
            "price": 50000.0,
            "timestamp": datetime.now(),
            "volume": 1000.0,
            "change_24h": 2.5
        }
        
        ltp = manager.get_ltp("BTCUSD")
        assert ltp == 50000.0
    
    def test_get_tick_data(self, manager):
        """Test get_tick_data returns full tick info"""
        from datetime import datetime
        
        tick_data = {
            "price": 50000.0,
            "timestamp": datetime.now(),
            "volume": 1000.0,
            "change_24h": 2.5
        }
        
        manager.ltp_cache["BTCUSD"] = tick_data
        
        result = manager.get_tick_data("BTCUSD")
        assert result == tick_data
        assert result["price"] == 50000.0
        assert result["volume"] == 1000.0
    
    @pytest.mark.asyncio
    async def test_handle_tick(self, manager):
        """Test tick processing and caching"""
        tick = {
            "symbol": "BTCUSD",
            "price": 50000.0,
            "timestamp": 1234567890,
            "volume": 1000.0,
            "change_24h": 2.5
        }
        
        await manager._handle_tick(tick)
        
        # Check cache updated
        assert "BTCUSD" in manager.ltp_cache
        assert manager.ltp_cache["BTCUSD"]["price"] == 50000.0
        assert manager.ltp_cache["BTCUSD"]["volume"] == 1000.0
    
    @pytest.mark.asyncio
    async def test_handle_multiple_ticks(self, manager):
        """Test handling multiple ticks for different symbols"""
        ticks = [
            {"symbol": "BTCUSD", "price": 50000.0, "timestamp": 123, "volume": 100},
            {"symbol": "ETHUSD", "price": 3000.0, "timestamp": 124, "volume": 200},
            {"symbol": "BTCUSD", "price": 50100.0, "timestamp": 125, "volume": 150}
        ]
        
        for tick in ticks:
            await manager._handle_tick(tick)
        
        # Check both symbols cached
        assert "BTCUSD" in manager.ltp_cache
        assert "ETHUSD" in manager.ltp_cache
        
        # Check latest price for BTCUSD
        assert manager.ltp_cache["BTCUSD"]["price"] == 50100.0
        assert manager.ltp_cache["ETHUSD"]["price"] == 3000.0
