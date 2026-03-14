import json
import os
from enum import Enum
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field
from core.config import settings, runtime_settings
from core.logger import logger, LogCategory

class SystemStateEnum(str, Enum):
    READY = "READY"
    COOLDOWN = "COOLDOWN"
    DAILY_LOCK = "DAILY_LOCK"   # Hit max loss or max trades
    WEEKLY_LOCK = "WEEKLY_LOCK" 
    PROFIT_LOCK = "PROFIT_LOCK" # Hit daily target
    KILL_SWITCH = "KILL_SWITCH" # Critical failure
    MANUAL_PAUSE = "MANUAL_PAUSE"

class GlobalState(BaseModel):
    state: SystemStateEnum = SystemStateEnum.READY
    
    # Counters
    trades_today: int = 0
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    
    last_update: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_trade_date: str = Field(default_factory=lambda: date.today().isoformat())
    last_source_heartbeat: Optional[str] = None

    def reset_daily_if_needed(self):
        today = date.today().isoformat()
        if self.last_trade_date != today:
            logger.audit(LogCategory.STATE, f"New day detected. Resetting daily stats. Previous: {self.last_trade_date}, New: {today}")
            self.trades_today = 0
            self.daily_pnl = 0.0
            self.consecutive_losses = 0 # Optional: decide if this resets daily
            self.last_trade_date = today
            # If we were in a daily lock, unlock (unless it's a permanent kill switch)
            if self.state in [SystemStateEnum.DAILY_LOCK, SystemStateEnum.PROFIT_LOCK, SystemStateEnum.COOLDOWN]:
                self.state = SystemStateEnum.READY
        return self

STATE_FILE = os.path.join(settings.DATA_DIR, "state.json")

class StateEngine:
    def __init__(self):
        self._state = self.load()
    
    @property
    def current(self) -> GlobalState:
        return self._state

    def load(self) -> GlobalState:
        if not os.path.exists(STATE_FILE):
            logger.audit(LogCategory.STATE, "No state file found. Initializing new GlobalState.")
            return GlobalState()
        
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
            state = GlobalState(**data)
            # Check date rollover immediately on load
            state.reset_daily_if_needed()
            return state
        except Exception as e:
            logger.critical(LogCategory.STATE, f"State corruption detected! Failing into KILL_SWITCH. Error: {e}")
            # Fail closed
            s = GlobalState()
            s.state = SystemStateEnum.KILL_SWITCH
            return s

    def save(self):
        self._state.last_update = datetime.now().isoformat()
        try:
            with open(STATE_FILE, 'w') as f:
                f.write(self._state.model_dump_json(indent=2))
        except Exception as e:
            logger.critical(LogCategory.STATE, f"Failed to save state! Error: {e}")
            # If we can't save state, we are flying blind. KILL SWITCH.
            self._state.state = SystemStateEnum.KILL_SWITCH
            
    def set_state(self, new_state: SystemStateEnum):
        logger.audit(LogCategory.STATE, f"DEBUG: set_state called with {new_state}")
        if self.current.state != new_state:
            old = self.current.state
            self.current.state = new_state
            logger.audit(LogCategory.STATE, f"State Transition: {old} -> {new_state}")
            logger.audit(LogCategory.STATE, f"DEBUG: State transition confirmed: {old} -> {new_state}")
            self._broadcast_state()
            
            # Notify via Telegram for critical transitions
            if new_state in [SystemStateEnum.DAILY_LOCK, SystemStateEnum.PROFIT_LOCK, SystemStateEnum.KILL_SWITCH]:
                from core.notifiers.telegram import notifier
                notifier.notify(f"State transitioned from {old} to {new_state}. Governance protocol enforced.", priority="HIGH")
        self.save() # Ensure state is saved after transition

    def _broadcast_state(self):
        """Broadcast state changes via WebSocket to all connected clients"""
        try:
            # Import here to avoid circular dependency
            from core.websocket import ws_manager
            import asyncio
            
            # Prepare state data for broadcast
            state_data = {
                "state": self.current.state.value,
                "trades_today": self.current.trades_today,
                "consecutive_losses": self.current.consecutive_losses,
                "daily_pnl": self.current.daily_pnl,
                "weekly_pnl": self.current.weekly_pnl,
                "last_update": self.current.last_update
            }
            
            # Broadcast asynchronously (fire and forget)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(ws_manager.broadcast_state_change(state_data))
            except RuntimeError:
                # No event loop running (e.g., during tests)
                pass
        except Exception as e:
            # Don't fail state transition if broadcast fails
            logger.debug(LogCategory.SYSTEM, f"Failed to broadcast state change: {e}")


    async def _flatten_all_positions(self):
        """Emergency Flattening via Position Manager"""
        try:
            from core.position_manager import position_manager
            await position_manager.flatten_all()
        except Exception as e:
            logger.debug(LogCategory.SYSTEM, f"Flattening failed: {e}")


    def update_source_heartbeat(self):
        self._state.last_source_heartbeat = datetime.now().isoformat()
        logger.system(LogCategory.SYSTEM, "Institutional Signal Pulse Received", user_visible=False)
        self.save()

    def validate_limits(self) -> tuple[bool, str]:
        """
        Stateful Discipline Check:
        Returns (is_allowed, reason)
        """
        disc = runtime_settings.discipline
        
        self._state.reset_daily_if_needed()
        s = self._state
        
        if s.state == SystemStateEnum.MANUAL_PAUSE:
            return False, "System manually paused by user."
            
        if s.trades_today >= disc.max_trades_per_day:
            self.set_state(SystemStateEnum.DAILY_LOCK)
            return False, f"Daily trade limit ({disc.max_trades_per_day}) reached."
            
        if s.daily_pnl <= disc.max_daily_loss:
            self.set_state(SystemStateEnum.DAILY_LOCK)
            return False, f"Maximum daily loss ({disc.max_daily_loss}) hit. Sentinel Protocol Locked."
            
        if s.daily_pnl >= disc.max_daily_profit:
            self.set_state(SystemStateEnum.PROFIT_LOCK)
            return False, f"Daily target ({disc.max_daily_profit}) achieved. Safeguarding profits."

        return True, "Authorized"

    def update_pnl(self, pnl: float):
        self._state.daily_pnl += pnl
        self._state.weekly_pnl += pnl
        
        if pnl != 0: # Actual P&L update
            if pnl < 0:
                self._state.consecutive_losses += 1
            else:
                self._state.consecutive_losses = 0
        else: # Just incrementing trade count on entry
            self._state.trades_today += 1
            
        # Re-validate state immediately after P&L change
        self.validate_limits()
        self.save()
    
    async def update_pnl_realtime(self, pnl: float):
        """
        Update daily P&L from position manager in real-time.
        Triggers profit lock or daily lock if limits exceeded.
        
        Args:
            pnl: Current total P&L (unrealized + realized)
        """
        self._state.daily_pnl = pnl
        
        # Check profit lock
        if pnl >= runtime_settings.discipline.max_daily_profit:
            logger.system(
                LogCategory.RISK,
                f"Profit target hit: ₹{pnl:.2f} >= ₹{runtime_settings.discipline.max_daily_profit}"
            )
            self.set_state(SystemStateEnum.PROFIT_LOCK)
            await self._flatten_all_positions()
            audit.critical(f"PROFIT LOCK triggered at ₹{pnl:.2f}")
        
        # Check max loss
        if pnl <= runtime_settings.discipline.max_daily_loss:
            logger.system(
                LogCategory.RISK,
                f"Max loss hit: ₹{pnl:.2f} <= ₹{runtime_settings.discipline.max_daily_loss}"
            )
            self.set_state(SystemStateEnum.DAILY_LOCK)
            await self._flatten_all_positions()
            audit.critical(f"DAILY LOCK triggered at ₹{pnl:.2f}")
        
        # Broadcast state change if limits hit
        if self._state.state in [SystemStateEnum.PROFIT_LOCK, SystemStateEnum.DAILY_LOCK]:
            self._broadcast_state()

# Global Singleton
state_engine = StateEngine()
