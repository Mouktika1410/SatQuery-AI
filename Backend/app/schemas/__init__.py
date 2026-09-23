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
from app.schemas.copernicus import (
    AOIBounds,
    Sentinel1ProductSummary,
    CopernicusSearchRequest,
    CopernicusSearchResponse,
    MatchedSARPair,
    CopernicusPairSearchRequest,
    CopernicusPairSearchResponse,
    CopernicusAcquisitionRequest,
    CopernicusAcquisitionResponse,
    CopernicusAuthStatus,
)

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
    "AOIBounds",
    "Sentinel1ProductSummary",
    "CopernicusSearchRequest",
    "CopernicusSearchResponse",
    "MatchedSARPair",
    "CopernicusPairSearchRequest",
    "CopernicusPairSearchResponse",
    "CopernicusAcquisitionRequest",
    "CopernicusAcquisitionResponse",
    "CopernicusAuthStatus",
]
