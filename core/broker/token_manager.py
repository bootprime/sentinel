from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import os
from core.logger import logger, LogCategory
from core.audit import audit

class TokenManager:
    """
    Manages broker token lifecycle, expiry tracking, and refresh logic.
    """
    
    TOKEN_METADATA_FILE = "data/token_metadata.json"
    
    # Token validity durations (in hours)
    TOKEN_LIFETIMES = {
        "DHAN": 24,
        "ZERODHA": 24,
        "UPSTOX": 24,
        "DELTA": 8760  # API keys don't expire (365 days as placeholder)
    }
    
    def __init__(self):
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load token metadata from disk"""
        if os.path.exists(self.TOKEN_METADATA_FILE):
            try:
                with open(self.TOKEN_METADATA_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                audit.error(f"Failed to load token metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Persist token metadata to disk"""
        try:
            os.makedirs(os.path.dirname(self.TOKEN_METADATA_FILE), exist_ok=True)
            with open(self.TOKEN_METADATA_FILE, "w") as f:
                json.dump(self.metadata, f, indent=4)
        except Exception as e:
            audit.error(f"Failed to save token metadata: {e}")
    
    def register_token(self, broker_name: str, token: str):
        """
        Register a new token and track its creation time.
        """
        self.metadata[broker_name] = {
            "token": token,
            "created_at": datetime.now().isoformat(),
            "lifetime_hours": self.TOKEN_LIFETIMES.get(broker_name, 24)
        }
        self._save_metadata()
        logger.system(LogCategory.SECURITY, f"Token registered for {broker_name}")
    
    def is_token_valid(self, broker_name: str) -> bool:
        """
        Check if the token is still valid based on creation time.
        """
        if broker_name not in self.metadata:
            return False
        
        meta = self.metadata[broker_name]
        created_at = datetime.fromisoformat(meta["created_at"])
        lifetime = timedelta(hours=meta["lifetime_hours"])
        expiry_time = created_at + lifetime
        
        return datetime.now() < expiry_time
    
    def get_time_remaining(self, broker_name: str) -> Optional[timedelta]:
        """
        Get the time remaining until token expiry.
        Returns None if token doesn't exist or is already expired.
        """
        if broker_name not in self.metadata:
            return None
        
        meta = self.metadata[broker_name]
        created_at = datetime.fromisoformat(meta["created_at"])
        lifetime = timedelta(hours=meta["lifetime_hours"])
        expiry_time = created_at + lifetime
        
        remaining = expiry_time - datetime.now()
        return remaining if remaining.total_seconds() > 0 else None
    
    def get_expiry_status(self, broker_name: str) -> Dict[str, Any]:
        """
        Get comprehensive expiry status for UI display.
        """
        if broker_name not in self.metadata:
            return {
                "valid": False,
                "message": "No token registered",
                "hours_remaining": 0
            }
        
        remaining = self.get_time_remaining(broker_name)
        
        if remaining is None:
            return {
                "valid": False,
                "message": "Token expired",
                "hours_remaining": 0
            }
        
        hours = remaining.total_seconds() / 3600
        
        return {
            "valid": True,
            "message": f"{int(hours)}h remaining",
            "hours_remaining": hours,
            "expires_at": (datetime.now() + remaining).isoformat()
        }
    
    def refresh_token_dhan(self, client_id: str, current_token: str) -> Optional[str]:
        """
        Attempt to refresh Dhan token using their refresh API.
        Returns new token if successful, None otherwise.
        """
        try:
            from dhanhq import dhanhq
            
            # Dhan's refresh endpoint (if available)
            # Note: As of now, Dhan doesn't have a public refresh API
            # This is a placeholder for future implementation
            logger.system(LogCategory.SECURITY, "Dhan token refresh not yet supported")
            return None
            
        except Exception as e:
            audit.error(f"Dhan token refresh failed: {e}")
            return None
    
    def clear_token(self, broker_name: str):
        """Remove token metadata for a broker"""
        if broker_name in self.metadata:
            del self.metadata[broker_name]
            self._save_metadata()
            logger.system(LogCategory.SECURITY, f"Token cleared for {broker_name}")

# Global instance
token_manager = TokenManager()
