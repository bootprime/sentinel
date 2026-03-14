from enum import Enum
from typing import Literal, Tuple, Optional
from pydantic import BaseModel, Field
import math
from core.contract import SignalDirection

class OptionMode(str, Enum):
    ATM = "ATM"
    ITM = "ITM"
    OTM = "OTM"

class ExpiryType(str, Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    AUTO = "AUTO"

class OptionConfig(BaseModel):
    option_mode: OptionMode = OptionMode.ATM
    strike_step: int = Field(default=50, description="Strike interval for the symbol")
    strike_offset: int = Field(default=0, ge=0, description="Number of steps deep/far")
    expiry_type: ExpiryType = ExpiryType.WEEKLY
    lot_size: int = Field(default=1, gt=0)
    max_premium_per_lot: Optional[float] = None # Budget constraint

class OptionSelector:
    @staticmethod
    def get_nearest_strike(price: float, step: int) -> int:
        return round(price / step) * step

    @classmethod
    def select_strike(cls, index_price: float, direction: SignalDirection, config: OptionConfig) -> int:
        """
        Pure function: Converts Index Price -> Option Strike based on config.
        """
        atm_strike = cls.get_nearest_strike(index_price, config.strike_step)
        
        step_value = config.strike_step * config.strike_offset
        
        if config.option_mode == OptionMode.ATM:
            return atm_strike
            
        if direction == SignalDirection.CALL:
            # ITM Call = Lower Strike
            # OTM Call = Higher Strike
            if config.option_mode == OptionMode.ITM:
                return atm_strike - step_value
            elif config.option_mode == OptionMode.OTM:
                return atm_strike + step_value
                
        elif direction == SignalDirection.PUT:
            # ITM Put = Higher Strike
            # OTM Put = Lower Strike
            if config.option_mode == OptionMode.ITM:
                return atm_strike + step_value
            elif config.option_mode == OptionMode.OTM:
                return atm_strike - step_value
                
        return atm_strike  # Fallback
    
    @classmethod
    def get_option_type(cls, direction: SignalDirection) -> str:
        return "CE" if direction == SignalDirection.CALL else "PE"

    @classmethod
    def solve(cls, index_price: float, direction: SignalDirection, config: OptionConfig) -> dict:
        strike = cls.select_strike(index_price, direction, config)
        opt_type = cls.get_option_type(direction)
        return {
            "strike": strike,
            "type": opt_type,
            "expiry_mode": config.expiry_type, # Execution adapter resolves actual date
            "lot_size": config.lot_size
        }
