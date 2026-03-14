"""
Shared pytest fixtures for Sentinel tests
"""

import pytest
import json
import os
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from core.config import settings, RuntimeConfig
from core.state import GlobalState, SystemStateEnum
from core.contract import SignalPayload, SignalDirection, Strategy


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Mock logger, audit, websocket, and broker libs for all tests"""
    import sys
    
    # Mock Logger
    mock_logger = MagicMock()
    monkeypatch.setattr("core.logger.logger", mock_logger)
    
    # Mock Audit
    mock_audit = MagicMock()
    monkeypatch.setattr("core.audit.audit", mock_audit)
    
    # Mock WebSocket Manager
    mock_ws = AsyncMock()
    monkeypatch.setattr("core.websocket.ws_manager", mock_ws)
    
    # Mock Broker Manager
    # We need to mock the MODULE 'core.broker.manager' or the OBJECT 'broker_manager'
    # But to prevent ImportErrors for 'kiteconnect' etc, we must mock those modules BEFORE import
    
    # Mock kiteconnect
    if 'kiteconnect' not in sys.modules:
        sys.modules['kiteconnect'] = MagicMock()
        sys.modules['kiteconnect.KiteConnect'] = MagicMock()
        sys.modules['kiteconnect.KiteTicker'] = MagicMock()
        
    # Mock dhanhq
    if 'dhanhq' not in sys.modules:
        sys.modules['dhanhq'] = MagicMock()
        
    # Mock broker manager instance if it's already imported or about to be
    mock_bm = AsyncMock()
    # Safe patch if module is loaded. If not, the mock modules above should handle import time.
    # monkeypatch.setattr("core.broker.manager.broker_manager", mock_bm)
    
@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return str(data_dir)


@pytest.fixture
def mock_state():
    """Create a mock GlobalState for testing"""
    return GlobalState(
        state=SystemStateEnum.READY,
        trades_today=0,
        consecutive_losses=0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        last_trade_date=datetime.now().date().isoformat()
    )


@pytest.fixture
def mock_signal():
    """Create a mock signal payload for testing"""
    return SignalPayload(
        signal_id="TEST_SIGNAL_001",
        timestamp=int(datetime.now().timestamp() * 1000),
        strategy=Strategy.TREND_PULLBACK,
        symbol="NIFTY",
        direction=SignalDirection.CALL,
        index_entry=21500.0,
        index_sl=21400.0,
        index_tp=21700.0,
        rr=2.0,
        bar_time="2026-02-14 10:30:00"
    )


@pytest.fixture
def mock_config():
    """Create a mock RuntimeConfig for testing"""
    return RuntimeConfig()


@pytest.fixture(autouse=True)
def reset_settings(temp_data_dir, monkeypatch):
    """Reset settings to use temporary directory for each test"""
    monkeypatch.setattr(settings, 'DATA_DIR', temp_data_dir)
