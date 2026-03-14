// WebSocket client wrapper for Sentinel frontend
// Handles connection, reconnection, and message routing

class SentinelWebSocket {
    constructor(url = 'ws://localhost:8001/ws') {
        this.url = url;
        this.ws = null;
        this.reconnectInterval = 3000; // 3 seconds
        this.reconnectTimer = null;
        this.isIntentionalClose = false;
        this.messageHandlers = new Map();
        this.connectionHandlers = [];
        this.disconnectionHandlers = [];
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('[WebSocket] Connected to Sentinel backend');
                this.isIntentionalClose = false;

                // Clear reconnect timer
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = null;
                }

                // Notify connection handlers
                this.connectionHandlers.forEach(handler => handler());
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('[WebSocket] Failed to parse message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                // Also notify disconnection handlers on error to trigger UI update
                this.disconnectionHandlers.forEach(handler => handler());
            };

            this.ws.onclose = () => {
                console.log('[WebSocket] Disconnected from Sentinel backend');

                // Notify disconnection handlers
                this.disconnectionHandlers.forEach(handler => handler());

                // Attempt reconnection unless intentionally closed
                if (!this.isIntentionalClose) {
                    console.log(`[WebSocket] Reconnecting in ${this.reconnectInterval}ms...`);
                    this.reconnectTimer = setTimeout(() => {
                        this.connect();
                    }, this.reconnectInterval);
                }
            };

        } catch (error) {
            console.error('[WebSocket] Connection failed:', error);
            // Retry connection
            this.reconnectTimer = setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        }
    }

    disconnect() {
        this.isIntentionalClose = true;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('[WebSocket] Cannot send message, not connected');
        }
    }

    handleMessage(message) {
        const { type, data, timestamp } = message;

        // Route message to registered handlers
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            handlers.forEach(handler => handler(data, timestamp));
        }

        // Log unhandled message types
        if (!this.messageHandlers.has(type) && type !== 'heartbeat') {
            console.log('[WebSocket] Unhandled message type:', type, data);
        }
    }

    // Register a handler for a specific message type
    on(messageType, handler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, []);
        }
        this.messageHandlers.get(messageType).push(handler);
    }

    // Remove a handler
    off(messageType, handler) {
        if (this.messageHandlers.has(messageType)) {
            const handlers = this.messageHandlers.get(messageType);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    // Register connection event handlers
    onConnect(handler) {
        this.connectionHandlers.push(handler);
    }

    onDisconnect(handler) {
        this.disconnectionHandlers.push(handler);
    }

    // Send heartbeat to server
    sendHeartbeat() {
        this.send({ type: 'heartbeat', timestamp: new Date().toISOString() });
    }

    // Send ping to server
    ping() {
        this.send({ type: 'ping', timestamp: new Date().toISOString() });
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

export default SentinelWebSocket;
