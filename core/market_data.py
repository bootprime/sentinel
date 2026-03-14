"""
Market Data Manager
Centralized real-time market data streaming and LTP caching
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable
from core.logger import logger, LogCategory
from core.audit import audit


class MarketDataManager:
    """
    Manages real-time market data streams from multiple brokers.
    Maintains LTP cache and broadcasts updates via WebSocket.
    
    Architecture:
    Broker WebSocket → Market Data Manager → LTP Cache → WebSocket Broadcast → Frontend
    """
    
    def __init__(self):
        self.ltp_cache: Dict[str, dict] = {}  # {symbol: {"price": float, "timestamp": datetime}}
        self.subscriptions: set = set()  # Active symbol subscriptions
        self.broker_streams: dict = {}  # {broker_name: WebSocketStream}
        self.running = False
        
    async def start(self, broker_name: str = "DELTA", testnet: bool = False):
        """
        Start market data streaming for a broker.
        
        Args:
            broker_name: Broker to stream from ("DELTA", "KITE", "DHAN")
            testnet: Use testnet environment
        """
        try:
            if broker_name.upper() == "DELTA":
                from core.broker.delta_ws import DeltaWebSocketStream
                
                stream = DeltaWebSocketStream(
                    testnet=testnet,
                    on_tick=self._handle_tick
                )
                
                await stream.connect()
                self.broker_streams[broker_name] = stream
                self.running = True
                
                logger.system(LogCategory.SYSTEM, f"Market data streaming started: {broker_name}")
            
            else:
                audit.warning(f"Market data streaming not yet supported for: {broker_name}")
                
        except Exception as e:
            audit.error(f"Failed to start market data streaming: {e}")
    
    async def subscribe(self, symbols: List[str], broker_name: str = "DELTA"):
        """
        Subscribe to real-time updates for symbols.
        
        Args:
            symbols: List of symbols to subscribe to
            broker_name: Broker to subscribe through
        """
        try:
            stream = self.broker_streams.get(broker_name)
            if not stream:
                audit.warning(f"No active stream for {broker_name}")
                return
            
            await stream.subscribe(symbols)
            self.subscriptions.update(symbols)
            
            logger.system(LogCategory.SYSTEM, f"Subscribed to {len(symbols)} symbols")
            
        except Exception as e:
            audit.error(f"Subscription failed: {e}")
    
    async def unsubscribe(self, symbols: List[str], broker_name: str = "DELTA"):
        """Unsubscribe from symbols"""
        try:
            stream = self.broker_streams.get(broker_name)
            if not stream:
                return
            
            await stream.unsubscribe(symbols)
            self.subscriptions.difference_update(symbols)
            
            logger.system(LogCategory.SYSTEM, f"Unsubscribed from {len(symbols)} symbols")
            
        except Exception as e:
            audit.error(f"Unsubscription failed: {e}")
    
    def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get cached LTP (instant, no API call).
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Last traded price or None if not cached
        """
        cached = self.ltp_cache.get(symbol)
        if cached:
            return cached["price"]
        return None
    
    def get_tick_data(self, symbol: str) -> Optional[dict]:
        """
        Get full tick data including timestamp and metadata.
        
        Returns:
            {
                "price": float,
                "timestamp": datetime,
                "volume": float,
                "change_24h": float
            }
        """
        return self.ltp_cache.get(symbol)
    
    async def _handle_tick(self, tick: dict):
        """
        Process incoming tick and broadcast.
        
        Tick format:
        {
            "symbol": "BTCUSD",
            "price": 50000.0,
            "timestamp": 1234567890,
            "volume": 1000.0,
            "change_24h": 2.5
        }
        """
        try:
            symbol = tick["symbol"]
            price = tick["price"]
            
            # Update cache
            self.ltp_cache[symbol] = {
                "price": price,
                "timestamp": datetime.now(),
                "volume": tick.get("volume", 0),
                "change_24h": tick.get("change_24h", 0)
            }
            
            # Broadcast to frontend via WebSocket
            await self._broadcast_tick(tick)
            
            logger.debug(LogCategory.EXECUTION, f"Tick: {symbol} @ {price}")
            
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Tick processing error: {e}")
    
    async def _broadcast_tick(self, tick: dict):
        """Broadcast tick to frontend via WebSocket"""
        try:
            from core.websocket import ws_manager
            
            await ws_manager.broadcast({
                "type": "market_tick",
                "data": {
                    "symbol": tick["symbol"],
                    "price": tick["price"],
                    "timestamp": tick.get("timestamp"),
                    "volume": tick.get("volume", 0),
                    "change_24h": tick.get("change_24h", 0)
                },
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Tick broadcast error: {e}")
    
    async def stop(self):
        """Stop all market data streams"""
        for broker_name, stream in self.broker_streams.items():
            try:
                await stream.disconnect()
                logger.system(LogCategory.SYSTEM, f"Stopped market data stream: {broker_name}")
            except Exception as e:
                audit.error(f"Error stopping stream {broker_name}: {e}")
        
        self.broker_streams.clear()
        self.subscriptions.clear()
        self.running = False


# Global instance
market_data_manager = MarketDataManager()
