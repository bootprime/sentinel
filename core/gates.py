import time
from datetime import datetime, time as datetime_time
from typing import Dict, Tuple
from core.config import runtime_settings, settings
from core.logger import logger, LogCategory
from core.state import state_engine, SystemStateEnum
from core.contract import SignalPayload, Strategy
from core.audit import audit

# In-memory TTL cache for deduplication
# Map: signal_id -> (timestamp_added)
_DEDUP_CACHE: Dict[str, float] = {}
_DEDUP_TTL_SECONDS = 300 # Keep signal IDs for 5 minutes to prevent replay

def _clean_dedup_cache():
    now = time.time()
    keys_to_remove = [k for k, v in _DEDUP_CACHE.items() if now - v > _DEDUP_TTL_SECONDS]
    for k in keys_to_remove:
        del _DEDUP_CACHE[k]

class GateException(Exception):
    pass

class SentinelGates:
    
    @staticmethod
    def freshness_gate(signal: SignalPayload):
        """
        Gate 1: Freshness
        Signal timestamp must be within MAX_SIGNAL_AGE_SECONDS of now.
        """
        now_ms = int(time.time() * 1000)
        age_verification_ms = settings.MAX_SIGNAL_AGE_SECONDS * 1000
        delta = now_ms - signal.timestamp
        
        if delta > age_verification_ms:
            # Check if it's negative (future signal? clock skew?)
            if delta < -1000: # Allow 1s clock skew
                 raise GateException(f"Freshness Gate Failed: Signal is from the future ({delta}ms)")
            raise GateException(f"Freshness Gate Failed: Signal too old. Age: {delta}ms > Limit: {age_verification_ms}ms")
            
        return True

    @staticmethod
    def dedup_gate(signal: SignalPayload):
        """
        Gate 2: Deduplication
        Signal ID must not be in the recent cache.
        """
        _clean_dedup_cache()
        if signal.signal_id in _DEDUP_CACHE:
            raise GateException(f"Dedup Gate Failed: Duplicate Signal ID {signal.signal_id}")
        
        # Add to cache (optimistic, but if later gates fail, we technically consumed the ID. 
        # This is fail-safe; better to drop a retry than execute twice.)
        _DEDUP_CACHE[signal.signal_id] = time.time()
        return True

    @staticmethod
    def strategy_whitelist_gate(signal: SignalPayload):
        """
        Gate 3: Strategy Whitelist
        Strategy must be enabled in config.
        """
        if signal.strategy not in settings.STRATEGY_WHITELIST:
             raise GateException(f"Strategy Gate Failed: {signal.strategy} is not in whitelist {settings.STRATEGY_WHITELIST}")
        return True

    @staticmethod
    def risk_reward_gate(signal: SignalPayload):
        """
        Gate 4: Risk/Reward
        RR must be >= Config Min.
        """
        min_rr = runtime_settings.discipline.min_rr_ratio
        if signal.rr < min_rr:
            raise GateException(f"RR Gate Failed: {signal.rr} < {min_rr}")
        return True

    @staticmethod
    def structure_logic_gate(signal: SignalPayload):
        """
        Gate 5: Structure
        Logical price levels.
        """
        try:
            signal.validate_logic()
        except ValueError as e:
            raise GateException(f"Structure Gate Failed: {e}")
        return True

    @staticmethod
    def session_gate(signal: SignalPayload):
        """
        Gate 6: Session Time
        Must be within trading hours and before last entry time.
        """
        disc = runtime_settings.discipline
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        if not (disc.session_start <= current_time_str <= disc.session_end):
             raise GateException(f"Session Gate Failed: Current time {current_time_str} outside session {disc.session_start}-{disc.session_end}")
        
        if current_time_str > disc.last_entry:
             raise GateException(f"Session Gate Failed: Past last entry time {disc.last_entry}")
             
        return True

    @staticmethod
    def state_gate():
        """
        Gate 7: System State
        Global State must be READY.
        """
        current_state = state_engine.current.state
        if current_state != SystemStateEnum.READY:
            raise GateException(f"State Gate Failed: System is in {current_state} state.")
        return True

    @classmethod
    def process(cls, signal: SignalPayload):
        """
        Runs all gates in sequence.
        Raises GateException if ANY gate fails.
        """
        logger.system(LogCategory.SIGNAL, f"Processing Gates for {signal.signal_id}...", signal_id=signal.signal_id)
        
        # 1. Freshness
        # The instruction provided an incomplete and syntactically incorrect snippet for freshness here.
        # Keeping the original call to freshness_gate for correctness.
        # If the intent was to move the logic here, it needs to be fully provided.
        # For now, applying the logging changes as per the instruction's spirit.
        
        try:
            cls.freshness_gate(signal)
            cls.dedup_gate(signal)
            cls.strategy_whitelist_gate(signal)
            cls.risk_reward_gate(signal)
            cls.structure_logic_gate(signal)
            cls.session_gate(signal)
            cls.state_gate()
            
            logger.system(LogCategory.SIGNAL, f"Signal {signal.signal_id} passed all gates.", signal_id=signal.signal_id)
            return True
            
        except GateException as e:
            audit.warning(f"Signal Rejected: {e}")
            raise e
        except Exception as e:
            audit.error(f"Unexpected Gate Error: {e}")
            raise e
