from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from core.contract import SignalDirection, SignalPayload
from core.option_engine import OptionConfig, OptionMode

class RiskTranslationMode(str, Enum):
    DELTA_APPROX = "DELTA_APPROX"
    PERCENTAGE = "PERCENTAGE"
    FIXED_PREMIUM = "FIXED_PREMIUM"

class RiskConfig(BaseModel):
    mode: RiskTranslationMode = RiskTranslationMode.PERCENTAGE
    
    # Mode: DELTA_APPROX
    assumed_delta_atm: float = 0.5
    assumed_delta_itm_step: float = 0.1  # Add 0.1 delta per step ITM
    assumed_delta_otm_step: float = 0.1  # Subtract 0.1 delta per step OTM
    
    # Mode: PERCENTAGE
    sl_percentage: float = 15.0  # 15% SL on premium
    tp_percentage: float = 30.0  # 30% TP on premium
    
    # Mode: FIXED_PREMIUM
    sl_points: float = 10.0
    tp_points: float = 20.0

class RiskTranslator:
    
    @classmethod
    def calculate_delta(cls, opt_config: OptionConfig, risk_config: RiskConfig) -> float:
        """
        Estimates delta based on strike offset and config.
        """
        base_delta = risk_config.assumed_delta_atm
        
        offset = opt_config.strike_offset
        if opt_config.option_mode == OptionMode.ATM:
            return base_delta
        
        if opt_config.option_mode == OptionMode.ITM:
            # ITM has higher delta
            delta = base_delta + (offset * risk_config.assumed_delta_itm_step)
            return min(delta, 0.95) # Cap at 0.95
            
        if opt_config.option_mode == OptionMode.OTM:
            # OTM has lower delta
            delta = base_delta - (offset * risk_config.assumed_delta_otm_step)
            return max(delta, 0.05) # Floor at 0.05
            
        return base_delta

    @classmethod
    def translate(cls, signal: SignalPayload, opt_config: OptionConfig, risk_config: RiskConfig, estimated_premium: float) -> dict:
        """
        Returns { "sl_price": float, "tp_price": float, "method": str }
        """
        method_used = risk_config.mode.value
        
        sl_price = 0.0
        tp_price = 0.0
        
        if risk_config.mode == RiskTranslationMode.PERCENTAGE:
            # Simple % of premium
            # SL = Premium - (Premium * SL%)
            # TP = Premium + (Premium * TP%)
            sl_dist = estimated_premium * (risk_config.sl_percentage / 100.0)
            tp_dist = estimated_premium * (risk_config.tp_percentage / 100.0)
            
            sl_price = max(0.05, estimated_premium - sl_dist)
            tp_price = estimated_premium + tp_dist

        elif risk_config.mode == RiskTranslationMode.FIXED_PREMIUM:
            # Fixed points
            sl_price = max(0.05, estimated_premium - risk_config.sl_points)
            tp_price = estimated_premium + risk_config.tp_points

        elif risk_config.mode == RiskTranslationMode.DELTA_APPROX:
            # Delta * Index Distance
            delta = cls.calculate_delta(opt_config, risk_config)
            
            index_sl_dist = abs(signal.index_entry - signal.index_sl)
            index_tp_dist = abs(signal.index_tp - signal.index_entry)
            
            opt_sl_dist = index_sl_dist * delta
            opt_tp_dist = index_tp_dist * delta
            
            sl_price = max(0.05, estimated_premium - opt_sl_dist)
            tp_price = estimated_premium + opt_tp_dist
            
            method_used += f" (Delta: {delta})"

        return {
            "sl_price": round(sl_price, 2),
            "tp_price": round(tp_price, 2),
            "method": method_used,
            "estimated_premium": estimated_premium
        }
