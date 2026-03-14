import pytest
import time
from unittest.mock import patch, MagicMock
from core.contract import SignalPayload, SignalDirection, Strategy
from core.gates import SentinelGates, GateException
from core.config import settings

def create_valid_signal():
    now = int(time.time() * 1000)
    return SignalPayload(
        signal_id=f"TEST_{now}",
        symbol="NIFTY",
        strategy=Strategy.TREND_PULLBACK,
        direction=SignalDirection.CALL,
        entry=100.0,
        sl=90.0,
        tp=120.0,
        rr=2.0,
        timestamp=now,
        bar_time="2023-01-01 10:00:00",
        strategy_version="1.0"
    )

def test_freshness_gate():
    sig = create_valid_signal()
    assert SentinelGates.freshness_gate(sig) is True
    
    # Old signal
    sig.timestamp -= (settings.MAX_SIGNAL_AGE_SECONDS + 1) * 1000
    with pytest.raises(GateException) as e:
        SentinelGates.freshness_gate(sig)
    assert "Signal too old" in str(e.value)

def test_dedup_gate():
    sig = create_valid_signal()
    assert SentinelGates.dedup_gate(sig) is True
    # Duplicate
    with pytest.raises(GateException) as e:
        SentinelGates.dedup_gate(sig)
    assert "Duplicate Signal" in str(e.value)

def test_risk_reward_gate():
    sig = create_valid_signal()
    sig.rr = 1.0 # Below 1.8
    with pytest.raises(GateException) as e:
        SentinelGates.risk_reward_gate(sig)
    assert "RR Gate Failed" in str(e.value)

def test_structure_gate():
    sig = create_valid_signal()
    sig.direction = SignalDirection.CALL
    # Logic: TP > Entry > SL
    sig.entry = 100
    sig.tp = 90 # Wrong
    sig.sl = 80
    
    with pytest.raises(GateException) as e:
        SentinelGates.structure_logic_gate(sig)
    assert "Structure Gate Failed" in str(e.value)

@patch('core.gates.state_engine')
def test_state_gate(mock_state):
    sig = create_valid_signal()
    mock_state.current.state = "READY"
    assert SentinelGates.state_gate() is True
    
    mock_state.current.state = "KILL_SWITCH"
    with pytest.raises(GateException) as e:
        SentinelGates.state_gate()
    assert "State Gate Failed" in str(e.value)
