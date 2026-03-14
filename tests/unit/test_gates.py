"""
Unit tests for the 7-phase gate system
"""

import pytest
import time
from datetime import datetime
from core.gates import SentinelGates, GateException, _DEDUP_CACHE
from core.contract import SignalPayload, SignalDirection, Strategy
from core.state import state_engine, SystemStateEnum


class TestFreshnessGate:
    """Test Gate 1: Freshness validation"""
    
    def test_fresh_signal_passes(self, mock_signal):
        """Test that a fresh signal passes the freshness gate"""
        # Signal created just now should pass
        assert SentinelGates.freshness_gate(mock_signal) is True
    
    def test_old_signal_fails(self, mock_signal):
        """Test that an old signal fails the freshness gate"""
        # Create signal with old timestamp (10 seconds ago)
        mock_signal.timestamp = int((time.time() - 10) * 1000)
        
        with pytest.raises(GateException, match="Signal too old"):
            SentinelGates.freshness_gate(mock_signal)
    
    def test_future_signal_fails(self, mock_signal):
        """Test that a future signal fails the freshness gate"""
        # Create signal with future timestamp
        mock_signal.timestamp = int((time.time() + 5) * 1000)
        
        with pytest.raises(GateException, match="from the future"):
            SentinelGates.freshness_gate(mock_signal)


class TestDedupGate:
    """Test Gate 2: Deduplication"""
    
    def setup_method(self):
        """Clear dedup cache before each test"""
        _DEDUP_CACHE.clear()
    
    def test_new_signal_passes(self, mock_signal):
        """Test that a new signal ID passes dedup gate"""
        assert SentinelGates.dedup_gate(mock_signal) is True
    
    def test_duplicate_signal_fails(self, mock_signal):
        """Test that a duplicate signal ID fails dedup gate"""
        # First signal should pass
        SentinelGates.dedup_gate(mock_signal)
        
        # Second signal with same ID should fail
        with pytest.raises(GateException, match="Duplicate Signal ID"):
            SentinelGates.dedup_gate(mock_signal)
    
    def test_different_signals_pass(self, mock_signal):
        """Test that different signal IDs pass dedup gate"""
        signal1 = mock_signal
        signal2 = mock_signal.model_copy()
        signal2.signal_id = "TEST_SIGNAL_002"
        
        assert SentinelGates.dedup_gate(signal1) is True
        assert SentinelGates.dedup_gate(signal2) is True


class TestStrategyWhitelistGate:
    """Test Gate 3: Strategy whitelist"""
    
    def test_whitelisted_strategy_passes(self, mock_signal):
        """Test that whitelisted strategy passes"""
        mock_signal.strategy = Strategy.TREND_PULLBACK
        assert SentinelGates.strategy_whitelist_gate(mock_signal) is True
    
    def test_non_whitelisted_strategy_fails(self, mock_signal):
        """Test that non-whitelisted strategy fails"""
        # Create a strategy not in whitelist (if any)
        # This test assumes TREND_PULLBACK is in whitelist
        # You may need to adjust based on actual config
        pass  # Placeholder - adjust based on actual strategies


class TestRiskRewardGate:
    """Test Gate 4: Risk/Reward ratio"""
    
    def test_good_rr_passes(self, mock_signal):
        """Test that signal with good R:R passes"""
        mock_signal.rr = 2.5  # Above minimum (1.8)
        assert SentinelGates.risk_reward_gate(mock_signal) is True
    
    def test_bad_rr_fails(self, mock_signal):
        """Test that signal with bad R:R fails"""
        mock_signal.rr = 1.0  # Below minimum (1.8)
        
        with pytest.raises(GateException, match="RR Gate Failed"):
            SentinelGates.risk_reward_gate(mock_signal)


class TestStructureLogicGate:
    """Test Gate 5: Structure validation"""
    
    def test_valid_structure_passes(self, mock_signal):
        """Test that valid price structure passes"""
        # CALL: entry < TP and entry > SL
        mock_signal.direction = SignalDirection.CALL
        mock_signal.index_entry = 21500.0
        mock_signal.index_sl = 21400.0
        mock_signal.index_tp = 21700.0
        
        assert SentinelGates.structure_logic_gate(mock_signal) is True
    
    def test_invalid_structure_fails(self, mock_signal):
        """Test that invalid price structure fails"""
        # Invalid: TP < Entry for CALL
        mock_signal.direction = SignalDirection.CALL
        mock_signal.index_entry = 21500.0
        mock_signal.index_sl = 21400.0
        mock_signal.index_tp = 21300.0  # Invalid!
        
        with pytest.raises(GateException, match="Structure Gate Failed"):
            SentinelGates.structure_logic_gate(mock_signal)


class TestSessionGate:
    """Test Gate 6: Session time validation"""
    
    def test_within_session_passes(self, mock_signal, monkeypatch):
        """Test that signal within session hours passes"""
        # Mock current time to be within session (10:00 AM)
        class MockDatetime:
            @staticmethod
            def now():
                class MockNow:
                    def strftime(self, fmt):
                        return "10:00"
                return MockNow()
        
        monkeypatch.setattr('core.gates.datetime', MockDatetime)
        assert SentinelGates.session_gate(mock_signal) is True
    
    def test_outside_session_fails(self, mock_signal, monkeypatch):
        """Test that signal outside session hours fails"""
        # Mock current time to be outside session (8:00 AM)
        class MockDatetime:
            @staticmethod
            def now():
                class MockNow:
                    def strftime(self, fmt):
                        return "08:00"
                return MockNow()
        
        monkeypatch.setattr('core.gates.datetime', MockDatetime)
        
        with pytest.raises(GateException, match="Session Gate Failed"):
            SentinelGates.session_gate(mock_signal)


class TestStateGate:
    """Test Gate 7: System state validation"""
    
    def test_ready_state_passes(self, mock_state):
        """Test that READY state passes"""
        state_engine._state = mock_state
        state_engine._state.state = SystemStateEnum.READY
        
        assert SentinelGates.state_gate() is True
    
    def test_locked_state_fails(self, mock_state):
        """Test that locked states fail"""
        state_engine._state = mock_state
        state_engine._state.state = SystemStateEnum.DAILY_LOCK
        
        with pytest.raises(GateException, match="State Gate Failed"):
            SentinelGates.state_gate()


class TestGateProcessing:
    """Test full gate processing pipeline"""
    
    def setup_method(self):
        """Setup for each test"""
        _DEDUP_CACHE.clear()
    
    def test_valid_signal_passes_all_gates(self, mock_signal, mock_state, monkeypatch):
        """Test that a valid signal passes all gates"""
        # Setup state
        state_engine._state = mock_state
        state_engine._state.state = SystemStateEnum.READY
        
        # Mock time to be within session
        class MockDatetime:
            @staticmethod
            def now():
                class MockNow:
                    def strftime(self, fmt):
                        return "10:00"
                return MockNow()
        
        monkeypatch.setattr('core.gates.datetime', MockDatetime)
        
        # Should pass all gates
        assert SentinelGates.process(mock_signal) is True
    
    def test_invalid_signal_fails_at_first_gate(self, mock_signal):
        """Test that invalid signal fails at appropriate gate"""
        # Make signal old to fail freshness gate
        mock_signal.timestamp = int((time.time() - 10) * 1000)
        
        with pytest.raises(GateException):
            SentinelGates.process(mock_signal)
