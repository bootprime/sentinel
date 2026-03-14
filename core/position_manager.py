"""
Position Manager
Tracks open positions and calculates real-time P&L with MTM (Mark-to-Market)
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from core.logger import logger, LogCategory
from core.audit import audit


@dataclass
class Position:
    """Represents a single trading position"""
    symbol: str
    entry_price: float
    quantity: int
    direction: str  # "LONG" or "SHORT"
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    def update_mtm(self, current_price: float):
        """
        Update Mark-to-Market P&L based on current price.
        
        Formula:
        - LONG: (current_price - entry_price) * quantity
        - SHORT: (entry_price - current_price) * quantity
        """
        self.current_price = current_price
        
        if self.direction == "LONG":
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        elif self.direction == "SHORT":
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
        else:
            self.unrealized_pnl = 0.0
    
    def to_dict(self) -> dict:
        """Convert position to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "direction": self.direction,
            "entry_time": self.entry_time.isoformat(),
            "current_price": self.current_price,
            "unrealized_pnl": round(self.unrealized_pnl, 2)
        }


class PositionManager:
    """
    Manages open positions and calculates real-time P&L.
    
    Features:
    - Track multiple positions
    - Real-time MTM calculation
    - Automatic P&L updates
    - Profit lock enforcement
    - WebSocket broadcasting
    """
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # {symbol: Position}
        self.realized_pnl: float = 0.0  # Closed position P&L
        self.running = False
        
    async def start(self):
        """Start position tracking and MTM updates"""
        self.running = True
        logger.system(LogCategory.SYSTEM, "Position manager started")
        
        # Start MTM update loop
        asyncio.create_task(self._mtm_update_loop())
    
    async def stop(self):
        """Stop position tracking"""
        self.running = False
        logger.system(LogCategory.SYSTEM, "Position manager stopped")
    
    def add_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        direction: str
    ):
        """
        Register new position after fill.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            quantity: Position size
            direction: "LONG" or "SHORT"
        """
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            direction=direction,
            entry_time=datetime.now()
        )
        
        self.positions[symbol] = position
        logger.system(LogCategory.EXECUTION, f"Position added: {symbol} {direction} {quantity} @ {entry_price}")
        
        # Subscribe to market data for this symbol
        asyncio.create_task(self._subscribe_to_symbol(symbol))
    
    def close_position(self, symbol: str, exit_price: float) -> float:
        """
        Close position and realize P&L.
        
        Args:
            symbol: Symbol to close
            exit_price: Exit price
            
        Returns:
            Realized P&L
        """
        if symbol not in self.positions:
            audit.warning(f"Attempted to close non-existent position: {symbol}")
            return 0.0
        
        position = self.positions[symbol]
        position.update_mtm(exit_price)
        
        # Realize P&L
        realized = position.unrealized_pnl
        self.realized_pnl += realized
        
        logger.system(
            LogCategory.EXECUTION,
            f"Position closed: {symbol} P&L: ₹{realized:.2f}"
        )
        
        # Remove from active positions
        del self.positions[symbol]
        
        # Broadcast P&L update
        asyncio.create_task(self._broadcast_pnl())
        
        return realized
    
    def get_total_pnl(self) -> float:
        """
        Get total P&L (unrealized + realized).
        
        Returns:
            Total P&L
        """
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return unrealized + self.realized_pnl
    
    def get_unrealized_pnl(self) -> float:
        """Get total unrealized P&L from open positions"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        return self.positions.copy()
    
    async def _subscribe_to_symbol(self, symbol: str):
        """Subscribe to market data for position tracking"""
        try:
            from core.market_data import market_data_manager
            
            if market_data_manager.running:
                await market_data_manager.subscribe([symbol])
                logger.debug(LogCategory.EXECUTION, f"Subscribed to market data: {symbol}")
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Market data subscription failed: {e}")
    
    async def _mtm_update_loop(self):
        """
        Continuous MTM update loop.
        Updates positions every 1 second with latest prices.
        """
        while self.running:
            try:
                await self._update_all_positions()
                await asyncio.sleep(1)  # Update every second
            except Exception as e:
                logger.debug(LogCategory.EXECUTION, f"MTM update error: {e}")
                await asyncio.sleep(5)  # Backoff on error
    
    async def _update_all_positions(self):
        """Update all positions with latest prices"""
        if not self.positions:
            return
        
        from core.market_data import market_data_manager
        
        for symbol, position in self.positions.items():
            # Get latest price from market data cache
            current_price = market_data_manager.get_ltp(symbol)
            
            if current_price:
                position.update_mtm(current_price)
        
        # Broadcast updated P&L
        await self._broadcast_pnl()
        
        # Check profit/loss limits
        await self._check_limits()
    
    async def _broadcast_pnl(self):
        """Broadcast P&L update to frontend via WebSocket"""
        try:
            from core.websocket import ws_manager
            
            pnl_data = {
                "total_pnl": round(self.get_total_pnl(), 2),
                "unrealized_pnl": round(self.get_unrealized_pnl(), 2),
                "realized_pnl": round(self.realized_pnl, 2),
                "positions": [pos.to_dict() for pos in self.positions.values()]
            }
            
            await ws_manager.broadcast({
                "type": "pnl_update",
                "data": pnl_data,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"P&L broadcast error: {e}")
    
    async def _check_limits(self):
        """
        Check profit/loss limits and trigger state changes.
        Integrates with state engine for profit lock and daily lock.
        """
        try:
            from core.state import state_engine
            total_pnl = self.get_total_pnl()
            
            # Update state engine with current P&L
            await state_engine.update_pnl_realtime(total_pnl)
            
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Limit check error: {e}")

    async def flatten_all(self):
        """Emergency Close: Flattens all open positions."""
        symbols = list(self.positions.keys())
        for symbol in symbols:
            # For paper mode or mock, we just realize at current price
            pos = self.positions[symbol]
            self.close_position(symbol, pos.current_price or pos.entry_price)
            logger.audit(LogCategory.EXECUTION, f"Emergency Flattened: {symbol}")

# Global instance
position_manager = PositionManager()
