"""
API v1 Router Aggregator.

Aggregates all Phase 1 feature endpoint routers.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.api.v1.endpoints import flood
from app.api.v1.endpoints import chat

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(flood.router, prefix="/flood", tags=["Flood Analysis"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Assistant"])
