# app/security.py
from __future__ import annotations
import os
from typing import Tuple

def _load_api_keys() -> set[str]:
    # Robust fallback: if env is missing *or empty*, use dev_123
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        raw = "dev_123"
    return {k.strip() for k in raw.split(",") if k.strip()}

API_KEYS = _load_api_keys()

def verify_api_key(authorization: str | None) -> Tuple[bool, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return False, "Missing Bearer token"
    key = authorization.split(" ", 1)[1].strip()
    if key not in API_KEYS:
        return False, "Invalid API key"
    return True, key
