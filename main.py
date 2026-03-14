from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from core.config import settings
from core.security import verify_token
from core.logger import logger, LogCategory
from core.audit import audit
from core import state
from core.websocket import ws_manager

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# CORS - Restricted to localhost (production-safe)
import os
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Routes
from api import heartbeat, signal, config, logs, auth, governance

# Protected Routes
app.include_router(heartbeat.router, prefix="/heartbeat", tags=["Heartbeat"])
app.include_router(signal.router, dependencies=[Depends(verify_token)])
app.include_router(config.router, dependencies=[Depends(verify_token)])
app.include_router(logs.router, dependencies=[Depends(verify_token)])
app.include_router(auth.router, dependencies=[Depends(verify_token)])
app.include_router(governance.router, dependencies=[Depends(verify_token)])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional communication.
    Clients connect here to receive live updates.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive messages from client (e.g., heartbeat responses, commands)
            data = await websocket.receive_json()
            
            # Handle client messages
            if data.get("type") == "heartbeat":
                # Update last heartbeat timestamp
                if websocket in ws_manager.client_metadata:
                    from datetime import datetime
                    ws_manager.client_metadata[websocket]["last_heartbeat"] = datetime.now().isoformat()
            
            elif data.get("type") == "ping":
                # Respond to ping with pong
                await ws_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            
            # Add more message handlers as needed
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(LogCategory.SYSTEM, f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.system(LogCategory.SYSTEM, "Sentinel System Starting Up...")
    logger.user(LogCategory.SYSTEM, "Sentinel Prime Interface Ready. Waiting for signals...")
    audit.info(f"Mode: {settings.MODE}")
    audit.info(f"Strategies: {settings.STRATEGY_WHITELIST}")
    
    # Load Delta product mappings
    from core.symbol_mapper import symbol_mapper
    symbol_mapper.load_delta_products()
    
    # Start WebSocket heartbeat loop in background
    heartbeat_task = asyncio.create_task(ws_manager.heartbeat_loop())
    logger.system(LogCategory.SYSTEM, "WebSocket heartbeat loop started")
    
    # Start token refresh scheduler
    from core.broker.token_refresh import token_refresh_scheduler
    token_refresh_task = asyncio.create_task(token_refresh_scheduler.start())
    logger.system(LogCategory.SECURITY, "Token refresh scheduler started")
    
    # Start market data streaming (if Delta is active broker)
    from core.market_data import market_data_manager
    from core.broker.manager import broker_manager
    
    if broker_manager.broker_name == "DELTA":
        # Get testnet setting from credentials
        import json
        import os
        if os.path.exists("data/credentials.json"):
            with open("data/credentials.json") as f:
                creds = json.load(f)
                testnet = creds.get("DELTA", {}).get("testnet", False)
                await market_data_manager.start("DELTA", testnet=testnet)
                logger.system(LogCategory.SYSTEM, "Market data streaming started for Delta")
    
    # Start position manager
    from core.position_manager import position_manager
    await position_manager.start()
    logger.system(LogCategory.SYSTEM, "Position manager started")
    
    yield
    
    # Shutdown
    heartbeat_task.cancel()
    await token_refresh_scheduler.stop()
    await market_data_manager.stop()
    await position_manager.stop()
    logger.system(LogCategory.SYSTEM, "Sentinel System Shutting Down...")

app.router.lifespan_context = lifespan


if __name__ == "__main__":
    from core.config import settings
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=settings.PORT)

