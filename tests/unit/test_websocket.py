"""
Unit tests for WebSocket Manager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from core.websocket import ConnectionManager


class TestConnectionManager:
    """Test WebSocket ConnectionManager"""
    
    @pytest.mark.asyncio
    async def test_connect_adds_connection(self):
        """Test that connect adds websocket to active connections"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws, "test_client")
        
        assert mock_ws in manager.active_connections
        assert "test_client" in manager.client_metadata[mock_ws]["client_id"]
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """Test that disconnect removes websocket from active connections"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        manager.disconnect(mock_ws)
        
        assert mock_ws not in manager.active_connections
        assert mock_ws not in manager.client_metadata
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """Test sending message to specific client"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        await manager.send_personal_message({"type": "test", "data": "hello"}, mock_ws)
        
        mock_ws.send_json.assert_called_with({"type": "test", "data": "hello"})
    
    @pytest.mark.asyncio
    async def test_broadcast_to_all_clients(self):
        """Test broadcasting message to all connected clients"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        
        await manager.broadcast({"type": "test", "data": "broadcast"})
        
        mock_ws1.send_json.assert_called_with({"type": "test", "data": "broadcast"})
        mock_ws2.send_json.assert_called_with({"type": "test", "data": "broadcast"})
    
    @pytest.mark.asyncio
    async def test_broadcast_excludes_client(self):
        """Test that broadcast can exclude specific client"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        
        await manager.broadcast({"type": "test"}, exclude=mock_ws1)
        
        mock_ws1.send_json.assert_not_called()
        mock_ws2.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_state_change(self):
        """Test broadcasting state change"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        
        state_data = {
            "state": "READY",
            "trades_today": 5,
            "daily_pnl": 1000.0
        }
        
        await manager.broadcast_state_change(state_data)
        
        # Check that send_json was called with correct structure
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "state_change"
        assert call_args["data"] == state_data
        assert "timestamp" in call_args
    
    @pytest.mark.asyncio
    async def test_broadcast_signal(self):
        """Test broadcasting signal event"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        
        signal_data = {"signal_id": "TEST_001", "direction": "CALL"}
        await manager.broadcast_signal(signal_data)
        
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "signal"
        assert call_args["data"] == signal_data
    
    @pytest.mark.asyncio
    async def test_broadcast_fill(self):
        """Test broadcasting fill event"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        
        fill_data = {"order_id": "ORD_001", "qty": 50}
        await manager.broadcast_fill(fill_data)
        
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "fill"
        assert call_args["data"] == fill_data
    
    @pytest.mark.asyncio
    async def test_broadcast_log(self):
        """Test broadcasting log entry"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        
        log_entry = {"level": "INFO", "message": "Test log"}
        await manager.broadcast_log(log_entry)
        
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "log"
        assert call_args["data"] == log_entry
    
    @pytest.mark.asyncio
    async def test_broadcast_token_expiry(self):
        """Test broadcasting token expiry warning"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws)
        
        token_data = {"broker": "KITE", "hours_remaining": 2}
        await manager.broadcast_token_expiry(token_data)
        
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "token_expiry"
        assert call_args["data"] == token_data
    
    def test_get_connection_count(self):
        """Test getting connection count"""
        manager = ConnectionManager()
        assert manager.get_connection_count() == 0
        
        # Add mock connections
        manager.active_connections = [MagicMock(), MagicMock()]
        assert manager.get_connection_count() == 2
    
    @pytest.mark.asyncio
    async def test_get_client_info(self):
        """Test getting client information"""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws, "test_client_123")
        
        client_info = manager.get_client_info()
        assert len(client_info) == 1
        assert client_info[0]["client_id"] == "test_client_123"
        assert "connected_at" in client_info[0]
        assert "last_heartbeat" in client_info[0]
    
    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_clients(self):
        """Test that broadcast handles disconnected clients gracefully"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        # Make ws1 raise exception (simulating disconnect)
        mock_ws1.send_json.side_effect = Exception("Connection closed")
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        
        await manager.broadcast({"type": "test"})
        
        # ws1 should be removed from active connections
        assert mock_ws1 not in manager.active_connections
        # ws2 should still be connected
        assert mock_ws2 in manager.active_connections
