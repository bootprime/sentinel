import secrets
import json
import os
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.audit import audit

SECRETS_FILE = "data/secrets.json"
security = HTTPBearer()

def get_or_create_token() -> str:
    """
    Retrieves the execution verification token or creates one if missing.
    This token is the KEY to the system.
    """
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, "r") as f:
                data = json.load(f)
                token = data.get("api_token")
                if token:
                    return token
        except Exception as e:
            audit.error(f"Failed to read secrets file: {e}")

    # Generate new high-entropy token
    new_token = secrets.token_urlsafe(32)
    try:
        os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)
        with open(SECRETS_FILE, "w") as f:
            json.dump({
                "api_token": new_token,
                "note": "DO NOT SHARE THIS TOKEN. Stick this in Sentinel Extension."
            }, f, indent=4)
        audit.warning(f"NEW SECURITY TOKEN GENERATED: {SECRETS_FILE}")
    except Exception as e:
        audit.critical(f"Failed to write secrets file: {e}")
        raise RuntimeError("Security Subsystem Failure")
    
    return new_token

# Load token once on module import
_CURRENT_TOKEN = get_or_create_token()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Dependency to enforce Bearer Token authentication.
    """
    if credentials.credentials != _CURRENT_TOKEN:
        audit.warning("Unauthorized Access Attempt Detected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authentication Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
