"""
Unit tests for Position Manager
"""

import pytest
import asyncio
from datetime import datetime
from core.position_manager import Position, PositionManager


class TestPosition:
    """Test Position dataclass"""
    
    def test_position_init(self):
        """Test position initialization"""
        pos = Position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="LONG",
            entry_time=datetime.now()
        )
        
        assert pos.symbol == "BTCUSD"
        assert pos.entry_price == 50000.0
        assert pos.quantity == 10
        assert pos.direction == "LONG"
        assert pos.unrealized_pnl == 0.0
    
    def test_update_mtm_long(self):
        """Test MTM calculation for LONG position"""
        pos = Position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="LONG",
            entry_time=datetime.now()
        )
        
        # Price goes up
        pos.update_mtm(51000.0)
        assert pos.current_price == 51000.0
        assert pos.unrealized_pnl == 10000.0  # (51000 - 50000) * 10
        
        # Price goes down
        pos.update_mtm(49000.0)
        assert pos.unrealized_pnl == -10000.0  # (49000 - 50000) * 10
    
    def test_update_mtm_short(self):
        """Test MTM calculation for SHORT position"""
        pos = Position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="SHORT",
            entry_time=datetime.now()
        )
        
        # Price goes down (profit for short)
        pos.update_mtm(49000.0)
        assert pos.unrealized_pnl == 10000.0  # (50000 - 49000) * 10
        
        # Price goes up (loss for short)
        pos.update_mtm(51000.0)
        assert pos.unrealized_pnl == -10000.0  # (50000 - 51000) * 10
    
    def test_to_dict(self):
        """Test position serialization"""
        pos = Position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="LONG",
            entry_time=datetime(2026, 1, 1, 12, 0, 0)
        )
        pos.update_mtm(51000.0)
        
        data = pos.to_dict()
        
        assert data["symbol"] == "BTCUSD"
        assert data["entry_price"] == 50000.0
        assert data["quantity"] == 10
        assert data["direction"] == "LONG"
        assert data["current_price"] == 51000.0
        assert data["unrealized_pnl"] == 10000.0


class TestPositionManager:
    """Test Position Manager"""
    
    @pytest.fixture(autouse=True)
    def mock_asyncio(self, monkeypatch):
        """Mock asyncio.create_task to avoid needing event loop"""
        mock_task = MagicMock()
        monkeypatch.setattr("asyncio.create_task", mock_task)
        return mock_task

    @pytest.fixture
    def manager(self):
        """Create position manager instance"""
        return PositionManager()
    
    def test_init(self, manager):
        """Test initialization"""
        assert manager.positions == {}
        assert manager.realized_pnl == 0.0
        assert manager.running == False
    
    def test_add_position(self, manager):
        """Test adding a position"""
        manager.add_position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="LONG"
        )
        
        assert "BTCUSD" in manager.positions
        pos = manager.positions["BTCUSD"]
        assert pos.entry_price == 50000.0
        assert pos.quantity == 10
        assert pos.direction == "LONG"
    
    def test_close_position(self, manager):
        """Test closing a position"""
        manager.add_position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="LONG"
        )
        
        # Close at profit
        realized = manager.close_position("BTCUSD", 51000.0)
        
        assert realized == 10000.0
        assert manager.realized_pnl == 10000.0
        assert "BTCUSD" not in manager.positions
    
    def test_get_total_pnl(self, manager):
        """Test total P&L calculation"""
        # Add position
        manager.add_position(
            symbol="BTCUSD",
            entry_price=50000.0,
            quantity=10,
            direction="LONG"
        )
        
        # Update price
        manager.positions["BTCUSD"].update_mtm(51000.0)
        
        # Total P&L = unrealized
        assert manager.get_total_pnl() == 10000.0
        
        # Close position
        manager.close_position("BTCUSD", 51000.0)
        
        # Total P&L = realized
        assert manager.get_total_pnl() == 10000.0
    
    def test_multiple_positions(self, manager):
        """Test managing multiple positions"""
        manager.add_position("BTCUSD", 50000.0, 10, "LONG")
        manager.add_position("ETHUSD", 3000.0, 50, "SHORT")
        
        # Update prices
        manager.positions["BTCUSD"].update_mtm(51000.0)  # +10000
        manager.positions["ETHUSD"].update_mtm(2900.0)   # +5000
        
        total_unrealized = manager.get_unrealized_pnl()
        assert total_unrealized == 15000.0
    
    def test_get_position(self, manager):
        """Test getting a specific position"""
        manager.add_position("BTCUSD", 50000.0, 10, "LONG")
        
        pos = manager.get_position("BTCUSD")
        assert pos is not None
        assert pos.symbol == "BTCUSD"
        
        pos = manager.get_position("UNKNOWN")
        assert pos is None
