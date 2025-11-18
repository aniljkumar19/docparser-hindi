"""V1 API router with API key authentication"""
from fastapi import APIRouter, Depends
from ..auth.api_key_auth import require_api_key

# Create v1 router with API key dependency
# All routes under /v1 will require API key authentication
router = APIRouter(
    prefix="/v1",
    tags=["v1"],
    dependencies=[Depends(require_api_key)],  # Protects all routes under /v1
)

# Note: Individual route endpoints are still defined in main.py
# This router is included to add the dependency protection
# Routes can also be moved here later for better organization

