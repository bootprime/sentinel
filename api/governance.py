from fastapi import APIRouter, HTTPException, Depends
from core.state import state_engine, SystemStateEnum
from core.security import verify_token
from core.logger import logger, LogCategory
from core.audit import audit
from core.position_manager import position_manager

router = APIRouter(prefix="/governance", tags=["Governance"])

@router.post("/kill", dependencies=[Depends(verify_token)])
async def emergency_kill_switch():
    """
    EMERGENCY KILL SWITCH:
    1. Sets system state to KILL_SWITCH
    2. Flattens all active positions immediately
    3. Blocks all future signals
    """
    try:
        audit.critical("MANUAL KILL SWITCH ACTIVATED VIA UI")
        logger.system(LogCategory.SECURITY, "Emergency Kill Switch Activated!", user_visible=True)
        
        # Transition state
        logger.system(LogCategory.STATE, f"DEBUG: Setting state to {SystemStateEnum.KILL_SWITCH}. Current: {state_engine.current.state}")
        state_engine.set_state(SystemStateEnum.KILL_SWITCH)
        logger.system(LogCategory.STATE, f"DEBUG: State after set: {state_engine.current.state}")
        
        # Flatten all positions
        await position_manager.flatten_all()
        
        return {"status": "success", "message": "Kill switch activated. All positions flattened."}
    except Exception as e:
        logger.error(f"Kill switch execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pause", dependencies=[Depends(verify_token)])
async def manual_pause():
    """
    MANUAL PAUSE:
    1. Sets system state to MANUAL_PAUSE
    2. Prevents new signal authorizations
    3. Keeps existing positions open (allows them to hit SL/TP)
    """
    try:
        audit.warning("SYSTEM MANUALLY PAUSED BY OPERATOR")
        logger.system(LogCategory.STATE, f"DEBUG: Pausing system. Current: {state_engine.current.state}")
        state_engine.set_state(SystemStateEnum.MANUAL_PAUSE)
        logger.system(LogCategory.STATE, f"DEBUG: State after pause: {state_engine.current.state}")
        
        return {"status": "success", "message": "System paused. No new entries will be authorized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
