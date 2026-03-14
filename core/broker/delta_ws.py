"""
Delta Exchange WebSocket Stream
Real-time market data streaming for Delta Exchange
"""

import asyncio
import json
import websocket
from typing import Callable, List, Optional
from core.logger import logger, LogCategory
from core.audit import audit


class DeltaWebSocketStream:
    """
    Delta Exchange WebSocket client for real-time market data.
    
    WebSocket URL: wss://socket.delta.exchange
    
    Message format:
    {
        "type": "subscribe",
        "payload": {
            "channels": [
                {"name": "v2/ticker", "symbols": ["BTCUSD"]}
            ]
        }
    }
    """
    
    WS_URL = "wss://socket.delta.exchange"
    WS_TESTNET_URL = "wss://testnet-socket.delta.exchange"
    
    def __init__(self, testnet: bool = False, on_tick: Optional[Callable] = None):
        self.ws_url = self.WS_TESTNET_URL if testnet else self.WS_URL
        self.ws = None
        self.on_tick = on_tick
        self.subscriptions = set()
        self.running = False
        
    async def connect(self):
        """Connect to Delta WebSocket"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Run WebSocket in background thread
            import threading
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            self.running = True
            logger.system(LogCategory.SYSTEM, "Delta WebSocket connected")
            
        except Exception as e:
            audit.error(f"Delta WebSocket connection failed: {e}")
    
    async def subscribe(self, symbols: List[str]):
        """
        Subscribe to ticker updates for symbols.
        
        Args:
            symbols: List of symbols (e.g., ["BTCUSD", "ETHUSD"])
        """
        if not self.ws:
            await self.connect()
        
        subscribe_msg = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {
                        "name": "v2/ticker",
                        "symbols": symbols
                    }
                ]
            }
        }
        
        try:
            self.ws.send(json.dumps(subscribe_msg))
            self.subscriptions.update(symbols)
            logger.system(LogCategory.SYSTEM, f"Delta subscribed to: {symbols}")
        except Exception as e:
            audit.error(f"Delta subscription failed: {e}")
    
    async def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from ticker updates"""
        if not self.ws:
            return
        
        unsubscribe_msg = {
            "type": "unsubscribe",
            "payload": {
                "channels": [
                    {
                        "name": "v2/ticker",
                        "symbols": symbols
                    }
                ]
            }
        }
        
        try:
            self.ws.send(json.dumps(unsubscribe_msg))
            self.subscriptions.difference_update(symbols)
            logger.system(LogCategory.SYSTEM, f"Delta unsubscribed from: {symbols}")
        except Exception as e:
            audit.error(f"Delta unsubscription failed: {e}")
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Delta ticker format:
            # {
            #     "type": "v2/ticker",
            #     "symbol": "BTCUSD",
            #     "close": 50000.0,
            #     "timestamp": 1234567890
            # }
            
            if data.get("type") == "v2/ticker":
                tick = {
                    "symbol": data.get("symbol"),
                    "price": float(data.get("close", 0)),
                    "timestamp": data.get("timestamp"),
                    "volume": data.get("volume", 0),
                    "change_24h": data.get("price_change_24h", 0)
                }
                
                # Call tick handler
                if self.on_tick:
                    asyncio.create_task(self.on_tick(tick))
                    
        except Exception as e:
            logger.debug(LogCategory.EXECUTION, f"Delta WebSocket message error: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        audit.error(f"Delta WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        self.running = False
        logger.system(LogCategory.SYSTEM, f"Delta WebSocket closed: {close_msg}")
    
    def _on_open(self, ws):
        """Handle WebSocket open"""
        logger.system(LogCategory.SYSTEM, "Delta WebSocket opened")
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws:
            self.ws.close()
            self.running = False
            logger.system(LogCategory.SYSTEM, "Delta WebSocket disconnected")
