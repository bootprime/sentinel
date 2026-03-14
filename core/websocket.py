"""
WebSocket Manager for Real-Time Communication
Handles bidirectional communication between backend and frontend clients.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime
from core.logger import logger, LogCategory


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to all connected clients.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_metadata[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat()
        }
        logger.system(LogCategory.SYSTEM, f"WebSocket client connected: {self.client_metadata[websocket]['client_id']}")
        
        # Send initial connection confirmation
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "client_id": self.client_metadata[websocket]["client_id"],
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            client_id = self.client_metadata.get(websocket, {}).get("client_id", "unknown")
            self.active_connections.remove(websocket)
            if websocket in self.client_metadata:
                del self.client_metadata[websocket]
            logger.system(LogCategory.SYSTEM, f"WebSocket client disconnected: {client_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(LogCategory.SYSTEM, f"Failed to send personal message: {e}")
    
    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """
        Broadcast message to all connected clients.
        Optionally exclude a specific client.
        """
        disconnected = []
        for connection in self.active_connections:
            if connection == exclude:
                continue
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.debug(LogCategory.SYSTEM, f"Broadcast error: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_state_change(self, state_data: dict):
        """Broadcast system state changes"""
        await self.broadcast({
            "type": "state_change",
            "data": state_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_signal(self, signal_data: dict):
        """Broadcast new signal received"""
        await self.broadcast({
            "type": "signal",
            "data": signal_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_fill(self, fill_data: dict):
        """Broadcast order fill event"""
        await self.broadcast({
            "type": "fill",
            "data": fill_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_log(self, log_entry: dict):
        """Broadcast log entry"""
        await self.broadcast({
            "type": "log",
            "data": log_entry,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_token_expiry(self, token_data: dict):
        """Broadcast token expiry warning"""
        await self.broadcast({
            "type": "token_expiry",
            "data": token_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def heartbeat_loop(self):
        """
        Send periodic heartbeat to all clients to keep connection alive.
        Runs in background task.
        """
        while True:
            await asyncio.sleep(5)  # Every 5 seconds
            await self.broadcast({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            })
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_client_info(self) -> List[Dict[str, Any]]:
        """Get information about all connected clients"""
        return [
            {
                "client_id": meta["client_id"],
                "connected_at": meta["connected_at"],
                "last_heartbeat": meta["last_heartbeat"]
            }
            for meta in self.client_metadata.values()
        ]


# Global singleton
ws_manager = ConnectionManager()
