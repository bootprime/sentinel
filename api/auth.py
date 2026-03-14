from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.security import verify_token
from core.broker.manager import broker_manager
from core.broker.token_manager import token_manager
from core.logger import logger, LogCategory
import json
import os

router = APIRouter(prefix="/auth", tags=["Authentication"])

class TokenUpdateRequest(BaseModel):
    broker_name: str
    access_token: str
    client_id: str = None

@router.get("/status", dependencies=[Depends(verify_token)])
async def get_auth_status():
    """
    Get current authentication status for the active broker.
    """
    from core.config import settings, SystemMode
    
    broker_name = broker_manager.broker_name
    expiry_status = token_manager.get_expiry_status(broker_name)
    
    # If MODE is LIVE but broker is NULL (no valid credentials), force invalid status
    if settings.MODE == SystemMode.LIVE and broker_name == "NULL":
        # Load credentials to get the intended broker
        try:
            with open("data/credentials.json", "r") as f:
                creds = json.load(f)
            intended_broker = creds.get("active_broker", "DHAN")
            
            return {
                "broker": intended_broker,
                "authenticated": False,
                "token_status": {
                    "valid": False,
                    "message": "LIVE mode requires credentials",
                    "hours_remaining": 0
                }
            }
        except:
            pass
    
    return {
        "broker": broker_name,
        "authenticated": broker_manager.execution_broker is not None,
        "token_status": expiry_status
    }

@router.post("/update-token", dependencies=[Depends(verify_token)])
async def update_token(request: TokenUpdateRequest):
    """
    Update broker token manually from UI.
    """
    try:
        # Load credentials file
        cred_path = "data/credentials.json"
        with open(cred_path, "r") as f:
            creds = json.load(f)
        
        # Update the token
        if request.broker_name not in creds:
            raise HTTPException(status_code=400, detail=f"Broker {request.broker_name} not configured")
        
        creds[request.broker_name]["access_token"] = request.access_token
        if request.client_id:
            creds[request.broker_name]["client_id"] = request.client_id
        
        # Save updated credentials
        with open(cred_path, "w") as f:
            json.dump(creds, f, indent=4)
        
        # Register token with manager
        token_manager.register_token(request.broker_name, request.access_token)
        
        # Re-authenticate broker
        from core.broker.factory import BrokerFactory
        instance = BrokerFactory.get_broker(request.broker_name)
        config = creds[request.broker_name]
        
        if instance.authenticate(config):
            broker_manager.execution_broker = instance
            broker_manager.data_broker = instance
            logger.system(LogCategory.SECURITY, f"Token updated and authenticated for {request.broker_name}")
            return {"status": "success", "message": "Token updated successfully"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed with new token")
            
    except Exception as e:
        logger.audit(LogCategory.SECURITY, f"Token update failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh", dependencies=[Depends(verify_token)])
async def refresh_token():
    """
    Attempt to refresh the current broker token automatically.
    """
    broker_name = broker_manager.broker_name
    
    if broker_name == "DHAN":
        # Attempt Dhan refresh (not yet supported)
        return {"status": "not_supported", "message": "Dhan auto-refresh not available. Please update token manually."}
    elif broker_name == "ZERODHA":
        return {"status": "not_supported", "message": "Zerodha requires manual login flow."}
    else:
        return {"status": "not_supported", "message": f"Auto-refresh not supported for {broker_name}"}
