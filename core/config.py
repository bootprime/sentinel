import os
import json
from enum import Enum
from typing import List, Set, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel

# Forward Reference Fix
# We need to import OptionConfig and RiskConfig, but they might cause circular imports if not careful.
# However, OptionConfig and RiskConfig depend on Enums which are fine.
from core.option_engine import OptionConfig
from core.risk_engine import RiskConfig

from core.contract import Strategy

class SystemMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"

class DisciplineConfig(BaseModel):
    max_trades_per_day: int = Field(default=3, gt=0)
    max_daily_loss: float = Field(default=-1000.0, le=0)
    max_daily_profit: float = Field(default=3000.0, ge=0)
    min_rr_ratio: float = Field(default=1.8, gt=0)
    trade_qty: int = Field(default=50, gt=0)
    session_start: str = Field(default="09:15")
    session_end: str = Field(default="15:30")
    last_entry: str = Field(default="14:30")

class RuntimeConfig(BaseModel):
    """
    User-configurable settings that can change at runtime via UI.
    """
    option: OptionConfig = Field(default_factory=OptionConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    discipline: DisciplineConfig = Field(default_factory=DisciplineConfig)
    
class Config(BaseSettings):
    # System
    APP_NAME: str = "Sentinel"
    VERSION: str = "1.0.0"
    MODE: SystemMode = SystemMode.PAPER
    PORT: int = Field(default=8001, description="Backend port")
    
    # Path
    DATA_DIR: str = Field(default="data", description="Directory to store state and logs")
    CONFIG_FILE: str = "user_config.json"

    # Risk Global Defaults
    MAX_SIGNAL_AGE_SECONDS: int = 6
    TIMEZONE: str = "Asia/Kolkata"

    # Strategies
    STRATEGY_WHITELIST: Set[Strategy] = {Strategy.TREND_PULLBACK, Strategy.RANGE_REJECTION}
    
    # Broker
    BROKER_API_KEY: str = Field(default="", exclude=True)
    BROKER_API_SECRET: str = Field(default="", exclude=True)
    
    # Hypercare / Safety
    MAX_QUANTITY_LIMIT: int = 1  # Rigid hardcap
    KILL_SWITCH_ON_STARTUP: bool = False # Safety check logic

    class Config:
        env_file = ".env"
        case_sensitive = True

# Global singleton
settings = Config()

# User Runtime Config Helper
def load_runtime_config() -> RuntimeConfig:
    path = os.path.join(settings.DATA_DIR, settings.CONFIG_FILE)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return RuntimeConfig(**data)
        except Exception as e:
            print(f"Failed to load user config: {e}. Using defaults.")
    return RuntimeConfig()

def save_runtime_config(conf: RuntimeConfig):
    path = os.path.join(settings.DATA_DIR, settings.CONFIG_FILE)
    with open(path, "w") as f:
        f.write(conf.model_dump_json(indent=2))

# Initialize Runtime Config
runtime_settings = load_runtime_config()

# Ensure data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)
