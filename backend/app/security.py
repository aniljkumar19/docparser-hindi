import os
from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import ApiKey

ENV_KEYS = [k.strip() for k in os.getenv("API_KEYS", "dev_123").split(",") if k.strip()]

def verify_api_key(authorization: str):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    key = authorization.split(" ",1)[1].strip()

    # Check DB first
    try:
        db: Session = SessionLocal()
        rec = db.query(ApiKey).filter_by(key=key, active=True).first()
        if rec:
            return key
    except Exception:
        pass

    # Fallback to env list
    if key in ENV_KEYS:
        return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
