"""
Schemas package — all Phase 1 Pydantic request/response models.
"""

from app.schemas.health import HealthResponse, DatabaseHealthResponse
from app.schemas.flood import (
    ImageValidationResult,
    UploadValidationResponse,
    FloodDetectionOptions,
    FloodDetectionResult,
    FloodPolygonResult,
    AffectedVillage,
    ImpactMetrics,
    PriorityScore,
    EvacuationCandidate,
    EvacuationCandidatesResult,
    PipelineResult,
)
from app.schemas.chat import ChatQuery, ChatResponse

__all__ = [
    "HealthResponse",
    "DatabaseHealthResponse",
    "ImageValidationResult",
    "UploadValidationResponse",
    "FloodDetectionOptions",
    "FloodDetectionResult",
    "FloodPolygonResult",
    "AffectedVillage",
    "ImpactMetrics",
    "PriorityScore",
    "EvacuationCandidate",
    "EvacuationCandidatesResult",
    "PipelineResult",
    "ChatQuery",
    "ChatResponse",
]
