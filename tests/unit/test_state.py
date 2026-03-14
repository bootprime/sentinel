"""
Unit tests for State Engine
"""

import pytest
import json
import os
from datetime import datetime, date
from core.state import StateEngine, GlobalState, SystemStateEnum


class TestGlobalState:
    """Test GlobalState model"""
    
    def test_default_state(self):
        """Test default state initialization"""
        state = GlobalState()
        assert state.state == SystemStateEnum.READY
        assert state.trades_today == 0
        assert state.consecutive_losses == 0
        assert state.daily_pnl == 0.0
        assert state.weekly_pnl == 0.0
    
    def test_reset_daily_if_needed_same_day(self):
        """Test that reset doesn't happen on same day"""
        state = GlobalState(
            trades_today=5,
            daily_pnl=1000.0,
            last_trade_date=date.today().isoformat()
        )
        state.reset_daily_if_needed()
        
        assert state.trades_today == 5
        assert state.daily_pnl == 1000.0
    
    def test_reset_daily_if_needed_new_day(self):
        """Test that reset happens on new day"""
        yesterday = date.today().replace(day=date.today().day - 1).isoformat()
        state = GlobalState(
            trades_today=5,
            daily_pnl=1000.0,
            consecutive_losses=2,
            state=SystemStateEnum.DAILY_LOCK,
            last_trade_date=yesterday
        )
        state.reset_daily_if_needed()
        
        assert state.trades_today == 0
        assert state.daily_pnl == 0.0
        assert state.consecutive_losses == 0
        assert state.state == SystemStateEnum.READY


class TestStateEngine:
    """Test StateEngine functionality"""
    
    def test_load_creates_new_state_if_missing(self, temp_data_dir):
        """Test that load creates new state if file doesn't exist"""
        engine = StateEngine()
        assert isinstance(engine.current, GlobalState)
        assert engine.current.state == SystemStateEnum.READY
    
    def test_save_and_load(self, temp_data_dir):
        """Test saving and loading state"""
        engine = StateEngine()
        engine._state.trades_today = 3
        engine._state.daily_pnl = 500.0
        engine.save()
        
        # Create new engine to load saved state
        engine2 = StateEngine()
        assert engine2.current.trades_today == 3
        assert engine2.current.daily_pnl == 500.0
    
    def test_set_state_transitions(self, temp_data_dir):
        """Test state transitions"""
        engine = StateEngine()
        assert engine.current.state == SystemStateEnum.READY
        
        engine.set_state(SystemStateEnum.DAILY_LOCK)
        assert engine.current.state == SystemStateEnum.DAILY_LOCK
    
    def test_validate_limits_ready(self, temp_data_dir):
        """Test validate_limits when system is ready"""
        engine = StateEngine()
        allowed, reason = engine.validate_limits()
        
        assert allowed is True
        assert reason == "Authorized"
    
    def test_validate_limits_max_trades(self, temp_data_dir):
        """Test validate_limits when max trades reached"""
        engine = StateEngine()
        engine._state.trades_today = 10  # Assuming max is 10
        
        allowed, reason = engine.validate_limits()
        
        assert allowed is False
        assert "trade limit" in reason.lower()
        assert engine.current.state == SystemStateEnum.DAILY_LOCK
    
    def test_validate_limits_max_loss(self, temp_data_dir):
        """Test validate_limits when max loss hit"""
        engine = StateEngine()
        engine._state.daily_pnl = -5000.0  # Assuming max loss is -3000
        
        allowed, reason = engine.validate_limits()
        
        assert allowed is False
        assert "loss" in reason.lower()
        assert engine.current.state == SystemStateEnum.DAILY_LOCK
    
    def test_validate_limits_max_profit(self, temp_data_dir):
        """Test validate_limits when max profit reached"""
        engine = StateEngine()
        engine._state.daily_pnl = 10000.0  # Assuming max profit is 5000
        
        allowed, reason = engine.validate_limits()
        
        assert allowed is False
        assert "profit" in reason.lower() or "target" in reason.lower()
        assert engine.current.state == SystemStateEnum.PROFIT_LOCK
    
    def test_validate_limits_manual_pause(self, temp_data_dir):
        """Test validate_limits when manually paused"""
        engine = StateEngine()
        engine.set_state(SystemStateEnum.MANUAL_PAUSE)
        
        allowed, reason = engine.validate_limits()
        
        assert allowed is False
        assert "paused" in reason.lower()
    
    def test_update_pnl_profit(self, temp_data_dir):
        """Test update_pnl with profit"""
        engine = StateEngine()
        initial_pnl = engine.current.daily_pnl
        
        engine.update_pnl(500.0)
        
        assert engine.current.daily_pnl == initial_pnl + 500.0
        assert engine.current.consecutive_losses == 0
    
    def test_update_pnl_loss(self, temp_data_dir):
        """Test update_pnl with loss"""
        engine = StateEngine()
        initial_pnl = engine.current.daily_pnl
        
        engine.update_pnl(-200.0)
        
        assert engine.current.daily_pnl == initial_pnl - 200.0
        assert engine.current.consecutive_losses == 1
    
    def test_update_pnl_consecutive_losses(self, temp_data_dir):
        """Test consecutive losses tracking"""
        engine = StateEngine()
        
        engine.update_pnl(-100.0)
        assert engine.current.consecutive_losses == 1
        
        engine.update_pnl(-150.0)
        assert engine.current.consecutive_losses == 2
        
        # Profit resets consecutive losses
        engine.update_pnl(200.0)
        assert engine.current.consecutive_losses == 0
    
    def test_update_pnl_increments_trade_count(self, temp_data_dir):
        """Test that update_pnl with 0 increments trade count"""
        engine = StateEngine()
        initial_count = engine.current.trades_today
        
        engine.update_pnl(0.0)
        
        assert engine.current.trades_today == initial_count + 1


class TestStateEngineCorruption:
    """Test state engine behavior with corrupted data"""
    
    def test_load_corrupted_state_triggers_kill_switch(self, temp_data_dir):
        """Test that corrupted state file triggers KILL_SWITCH"""
        # Create corrupted state file
        state_file = os.path.join(temp_data_dir, "state.json")
        with open(state_file, 'w') as f:
            f.write("{ invalid json }")
        
        engine = StateEngine()
        assert engine.current.state == SystemStateEnum.KILL_SWITCH
    
    def test_save_failure_triggers_kill_switch(self, temp_data_dir, monkeypatch):
        """Test that save failure triggers KILL_SWITCH"""
        engine = StateEngine()
        
        # Mock open to raise exception
        def mock_open(*args, **kwargs):
            raise IOError("Disk full")
        
        monkeypatch.setattr('builtins.open', mock_open)
        
        engine.save()
        assert engine.current.state == SystemStateEnum.KILL_SWITCH
