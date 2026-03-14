from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from datetime import datetime

# from core.config import settings, Strategy <-- circular import risk. Strategy is fine if moved or kept basic.
# But Strategy was defined in config.py. Let's assume Strategy remains there.
# If config imports contract(via option_engine -> contract), then contract cannot import config.
# SOLUTION: Move Strategy and Enums to a `types.py` or keep Strategy in config but import inside validator for settings.
# Ideally, Strategy enum should be in contract.py or types.py. 
# For now, I will import config INSIDE the methods that need it.


class Strategy(str, Enum):
    TREND_PULLBACK = "TREND_PULLBACK"
    RANGE_REJECTION = "RANGE_REJECTION"

class SignalDirection(str, Enum):
    CALL = "CALL"
    PUT = "PUT"

class SignalSource(str, Enum):
    EXTENSION = "EXTENSION"
    WEBHOOK = "WEBHOOK"
    API = "API"
    
class SignalPayload(BaseModel):
    signal_id: str = Field(..., description="Unique ID per bar/signal")
    symbol: str = Field(..., description="Index Symbol e.g. NIFTY")
    strategy: Strategy
    direction: SignalDirection
    
    # Index Levels
    index_entry: float = Field(..., gt=0, description="Index Entry Price")
    index_sl: float = Field(..., gt=0, description="Index Stop Loss")
    index_tp: float = Field(..., gt=0, description="Index Take Profit")
    
    rr: float = Field(..., description="Risk Reward Ratio")
    
    # Time
    timestamp: int = Field(..., description="Epoch milliseconds")
    bar_time: str = Field(..., description="ISO Time of the candle bar")
    
    strategy_version: str = "1.0"
    source: SignalSource = SignalSource.EXTENSION
    
    @field_validator('rr')
    @classmethod
    def validate_rr(cls, v: float, info: ValidationInfo) -> float:
        from core.config import runtime_settings
        limit = runtime_settings.discipline.min_rr_ratio
        if v < limit:
            raise ValueError(f"RR {v} is below minimum authorized {limit}")
        return v
    
    def validate_logic(self):
        """
        Structural Logic Gate (Index Levels):
        CALL -> TP > Entry > SL
        PUT -> SL > Entry > TP
        """
        if self.direction == SignalDirection.CALL:
            if not (self.index_tp > self.index_entry > self.index_sl):
                raise ValueError(f"Invalid CALL structure: TP({self.index_tp}) > Entry({self.index_entry}) > SL({self.index_sl}) is FALSE")
        elif self.direction == SignalDirection.PUT:
            if not (self.index_sl > self.index_entry > self.index_tp):
                raise ValueError(f"Invalid PUT structure: SL({self.index_sl}) > Entry({self.index_entry}) > TP({self.index_tp}) is FALSE")
        return True
