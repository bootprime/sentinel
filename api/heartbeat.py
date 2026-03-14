from fastapi import APIRouter, Depends
from core.state import state_engine
from core.security import verify_token
from core.config import settings
from core.broker.manager import broker_manager

router = APIRouter()

@router.get("/")
async def heartbeat():
    return {
        "status": "alive",
        "system_state": state_engine.current.state,
        "mode": settings.MODE,
        "execution_broker": broker_manager.broker_name,
        "last_source_heartbeat": state_engine.current.last_source_heartbeat
    }

@router.post("/source/heartbeat", dependencies=[Depends(verify_token)])
async def source_heartbeat():
    """Extension health check"""
    state_engine.update_source_heartbeat()
    return {"status": "ok"}
