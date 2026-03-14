import logging
import json
import sys
import os
from datetime import datetime
from enum import Enum
from logging.handlers import RotatingFileHandler
from core.config import settings

# 1. Enums for Structure
class LogLevel(str, Enum):
    USER = "USER"       # Visible to End User (UI Default)
    SYSTEM = "SYSTEM"   # Visible to Power User (UI Toggle)
    AUDIT = "AUDIT"     # Compliance / Security (File Only / Export)
    DEBUG = "DEBUG"     # Dev Only (File Only)

class LogCategory(str, Enum):
    SIGNAL = "SIGNAL"
    EXECUTION = "EXECUTION"
    RISK = "RISK"
    STATE = "STATE"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM" # Generic

# 2. JSON Formatter
class SentinelJsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": getattr(record, "level", record.levelname),
            "category": getattr(record, "category", "SYSTEM"),
            "signal_id": getattr(record, "signal_id", None),
            "message": record.getMessage(),
            "user_visible": getattr(record, "user_visible", record.levelname in ["USER", "SYSTEM"])
        }
        
        # Exception Traceback (Debug only)
        if record.exc_info and record.levelname == "DEBUG":
             log_record["traceback"] = self.formatException(record.exc_info)
             
        return json.dumps(log_record)

# 3. The Logger Class
class SentinelLogger:
    def __init__(self):
        self._logger = logging.getLogger("SentinelCore")
        self._logger.setLevel(logging.DEBUG) # Catch all, filter by handler
        self._setup_handlers()

    def _setup_handlers(self):
        if self._logger.handlers:
            return

        formatter = SentinelJsonFormatter()
        log_file = os.path.join(settings.DATA_DIR, "sentinel.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # File Handler (Rotates at 5MB, keeps 5 backups)
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

        # Console Handler (For Development, JSON)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO) # Don't spam console with DEBUG
        ch.setFormatter(formatter)
        self._logger.addHandler(ch)

    async def _do_broadcast(self, log_record: dict):
        """Internal async helper for broadcasting."""
        try:
            from core.websocket import ws_manager
            await ws_manager.broadcast_log(log_record)
        except Exception:
            pass # Never let logging broadcast kill the main process

    def _emit(self, level_name: str, category: LogCategory, message: str, **kwargs):
        """Internal emitter"""
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "level": level_name,
            "category": category,
            "signal_id": kwargs.get("signal_id"),
            "message": message,
            "user_visible": kwargs.get("user_visible", level_name in [LogLevel.USER, LogLevel.SYSTEM])
        }
        
        # Standard Logging
        extra = {
            "category": category,
            "signal_id": log_record["signal_id"],
            "user_visible": log_record["user_visible"]
        }
        
        std_level = logging.INFO
        if level_name == LogLevel.DEBUG: std_level = logging.DEBUG
        if level_name == LogLevel.AUDIT: std_level = logging.WARNING
        
        self._logger.log(std_level, message, extra=extra)

        if log_record["user_visible"]:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._do_broadcast(log_record))
            except RuntimeError:
                # No running loop, can't broadcast real-time
                pass

    # --- Public API ---

    def user(self, category: LogCategory, message: str, signal_id: str = None, **kwargs):
        """Level: USER (Always Visible)"""
        self._emit(LogLevel.USER, category, message, signal_id=signal_id, **kwargs)

    def system(self, category: LogCategory, message: str, signal_id: str = None, **kwargs):
        """Level: SYSTEM (Advanced Visible)"""
        self._emit(LogLevel.SYSTEM, category, message, signal_id=signal_id, **kwargs)

    def audit(self, category: LogCategory, message: str, signal_id: str = None, **kwargs):
        """Level: AUDIT (Compliance / Secure)"""
        self._emit(LogLevel.AUDIT, category, message, signal_id=signal_id, **kwargs)

    def debug(self, category: LogCategory, message: str, signal_id: str = None, exc_info=None):
        """Level: DEBUG (Dev Only)"""
        extra = {
            "category": category,
            "signal_id": signal_id,
            "user_visible": False
        }
        self._logger.debug(message, exc_info=exc_info, extra=extra)

    # Legacy Shim (for gradual migration if needed)
    def info(self, msg): self.system(LogCategory.SYSTEM, msg)
    def warning(self, msg): self.system(LogCategory.SYSTEM, msg) # Warns are usually system-relevant
    def error(self, msg): self.system(LogCategory.SYSTEM, msg)
    def critical(self, msg): self.audit(LogCategory.SYSTEM, msg)

# Global Instance
logger = SentinelLogger()
