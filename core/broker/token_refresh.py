"""
Token Auto-Refresh Scheduler
Monitors token expiry and triggers refresh/notifications automatically.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from core.broker.token_manager import token_manager
from core.logger import logger, LogCategory
from core.audit import audit


class TokenRefreshScheduler:
    """
    Background scheduler that monitors token expiry and triggers refresh.
    Sends notifications via WebSocket when tokens are expiring.
    """
    
    # Warning thresholds (hours before expiry)
    WARNING_THRESHOLD_HOURS = 4
    CRITICAL_THRESHOLD_HOURS = 1
    
    def __init__(self):
        self.running = False
        self.check_interval = 300  # Check every 5 minutes
        self.warned_brokers = set()  # Track which brokers we've warned about
        
    async def start(self):
        """Start the token refresh scheduler"""
        self.running = True
        logger.system(LogCategory.SECURITY, "Token refresh scheduler started")
        
        while self.running:
            try:
                await self._check_all_tokens()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                audit.error(f"Token refresh scheduler error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the token refresh scheduler"""
        self.running = False
        logger.system(LogCategory.SECURITY, "Token refresh scheduler stopped")
    
    async def _check_all_tokens(self):
        """Check all registered tokens for expiry"""
        for broker_name in token_manager.metadata.keys():
            await self._check_token(broker_name)
    
    async def _check_token(self, broker_name: str):
        """Check a specific broker's token"""
        status = token_manager.get_expiry_status(broker_name)
        
        if not status["valid"]:
            # Token expired - attempt refresh
            await self._handle_expired_token(broker_name)
            return
        
        hours_remaining = status["hours_remaining"]
        
        # Critical warning (< 1 hour)
        if hours_remaining < self.CRITICAL_THRESHOLD_HOURS:
            await self._send_critical_warning(broker_name, hours_remaining)
        
        # Standard warning (< 4 hours)
        elif hours_remaining < self.WARNING_THRESHOLD_HOURS:
            await self._send_warning(broker_name, hours_remaining)
        
        # Reset warning flag if token is refreshed
        elif broker_name in self.warned_brokers:
            self.warned_brokers.remove(broker_name)
    
    async def _handle_expired_token(self, broker_name: str):
        """Handle expired token - attempt refresh or notify user"""
        logger.system(LogCategory.SECURITY, f"Token expired for {broker_name}, attempting refresh")
        
        # Attempt automatic refresh
        success = await self._attempt_refresh(broker_name)
        
        if success:
            logger.system(LogCategory.SECURITY, f"Token successfully refreshed for {broker_name}")
            self.warned_brokers.discard(broker_name)
            await self._broadcast_refresh_success(broker_name)
        else:
            # Refresh failed - notify user for manual intervention
            logger.system(LogCategory.SECURITY, f"Token refresh failed for {broker_name}, user intervention required")
            await self._broadcast_refresh_failed(broker_name)
    
    async def _attempt_refresh(self, broker_name: str) -> bool:
        """Attempt to refresh token for a broker"""
        try:
            if broker_name.upper() == "KITE" or broker_name.upper() == "ZERODHA":
                # Zerodha requires manual login flow
                return False
            
            elif broker_name.upper() == "DHAN":
                # Dhan doesn't support auto-refresh yet
                return False
            
            elif broker_name.upper() == "DELTA":
                # Delta Exchange supports API key rotation
                # API keys don't expire but can be rotated for security
                # For now, we'll just log that Delta keys are long-lived
                logger.system(LogCategory.SECURITY, f"Delta API keys are long-lived (no refresh needed)")
                return True  # Delta keys don't need refresh
            
            else:
                logger.system(LogCategory.SECURITY, f"Unknown broker: {broker_name}")
                return False
                
        except Exception as e:
            audit.error(f"Token refresh error for {broker_name}: {e}")
            return False
    
    async def _refresh_delta_token(self, broker_name: str) -> bool:
        """Refresh Delta Exchange token"""
        # Placeholder for Delta token refresh
        # Will be implemented when Delta broker adapter is created
        return False
    
    async def _send_warning(self, broker_name: str, hours_remaining: float):
        """Send standard warning about token expiry"""
        if broker_name in self.warned_brokers:
            return  # Already warned
        
        self.warned_brokers.add(broker_name)
        
        logger.system(
            LogCategory.SECURITY,
            f"Token expiry warning: {broker_name} token expires in {hours_remaining:.1f} hours"
        )
        
        await self._broadcast_token_warning(broker_name, hours_remaining, "warning")
    
    async def _send_critical_warning(self, broker_name: str, hours_remaining: float):
        """Send critical warning about imminent token expiry"""
        logger.system(
            LogCategory.SECURITY,
            f"CRITICAL: {broker_name} token expires in {hours_remaining:.1f} hours!"
        )
        
        await self._broadcast_token_warning(broker_name, hours_remaining, "critical")
    
    async def _broadcast_token_warning(self, broker_name: str, hours_remaining: float, severity: str):
        """Broadcast token expiry warning via WebSocket"""
        try:
            from core.websocket import ws_manager
            
            await ws_manager.broadcast_token_expiry({
                "broker": broker_name,
                "hours_remaining": hours_remaining,
                "severity": severity,
                "message": f"{broker_name} token expires in {hours_remaining:.1f} hours"
            })
        except Exception as e:
            logger.debug(LogCategory.SECURITY, f"Failed to broadcast token warning: {e}")
    
    async def _broadcast_refresh_success(self, broker_name: str):
        """Broadcast successful token refresh"""
        try:
            from core.websocket import ws_manager
            
            await ws_manager.broadcast({
                "type": "token_refresh_success",
                "data": {
                    "broker": broker_name,
                    "message": f"{broker_name} token refreshed successfully"
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.debug(LogCategory.SECURITY, f"Failed to broadcast refresh success: {e}")
    
    async def _broadcast_refresh_failed(self, broker_name: str):
        """Broadcast failed token refresh - requires manual intervention"""
        try:
            from core.websocket import ws_manager
            
            await ws_manager.broadcast_token_expiry({
                "broker": broker_name,
                "hours_remaining": 0,
                "severity": "expired",
                "message": f"{broker_name} token expired - manual refresh required"
            })
        except Exception as e:
            logger.debug(LogCategory.SECURITY, f"Failed to broadcast refresh failure: {e}")


# Global scheduler instance
token_refresh_scheduler = TokenRefreshScheduler()
