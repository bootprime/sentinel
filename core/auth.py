"""
Simple API Key Authentication Middleware
Lightweight security for production deployment
"""

from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
import os
import secrets

# API Key configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Load API key from environment or generate one
SENTINEL_API_KEY = os.getenv("SENTINEL_API_KEY")

if not SENTINEL_API_KEY:
    # Generate a secure random key for first run
    SENTINEL_API_KEY = secrets.token_urlsafe(32)
    print(f"\n{'='*60}")
    print(f"⚠️  IMPORTANT: No API key found!")
    print(f"Generated new API key: {SENTINEL_API_KEY}")
    print(f"Set environment variable: SENTINEL_API_KEY={SENTINEL_API_KEY}")
    print(f"Or add to .env file")
    print(f"{'='*60}\n")


async def verify_api_key(request: Request):
    """
    Verify API key for protected endpoints.
    Lightweight - only checks header, no database lookups.
    """
    # Skip auth for health check
    if request.url.path == "/health":
        return
    
    # Get API key from header
    api_key = request.headers.get(API_KEY_NAME)
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Include X-API-Key header."
        )
    
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, SENTINEL_API_KEY):
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
