"""
Impact Priority Scoring Service.

Computes transparent heuristic priority scores for affected areas.
Scores are based on normalized factors (population, buildings, roads).
Clearly labeled as decision-support heuristics, NOT validated ML predictions.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "population": 0.5,
    "buildings": 0.3,
    "roads": 0.2,
}


class ImpactScoringService:
    """
    Heuristic priority scoring for flood-affected zones.

    Scores are computed from normalized factors with configurable weights.
    This is a transparent decision-support tool, not a machine learning model.
    """

    def compute_priority_scores(
        self,
        exposure_data: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Score and rank affected villages by impact severity.

        Args:
            exposure_data: Dict matching ImpactMetrics schema from ExposureAnalysisService
            weights: Optional weight overrides for {population, buildings, roads}

        Returns:
            List of dicts matching PriorityScore schema, sorted by score descending.
        """
        effective_weights = {**_DEFAULT_WEIGHTS, **(weights or {})}
        # Normalize weights to sum to 1.0
        total_w = sum(effective_weights.values())
        if total_w > 0:
            effective_weights = {k: v / total_w for k, v in effective_weights.items()}

        villages = exposure_data.get("affected_villages", [])
        if not villages:
            return []

        affected_population = exposure_data.get("affected_population")
        affected_buildings = exposure_data.get("affected_buildings")
        affected_road_km = exposure_data.get("affected_road_length_km")

        # Build per-village raw factor values
        # We use flooded area as a proxy for village-level population/buildings/roads
        # when village-level breakdown isn't available
        max_area = max((v.get("area_flooded_km2", 0.0) for v in villages), default=1.0)
        if max_area <= 0:
            max_area = 1.0

        # Max values for normalization across all villages
        max_pop = max(
            (v.get("population_affected") or 0 for v in villages), default=1
        ) or 1
        if affected_population and affected_population > 0:
            max_pop = affected_population

        scored = []
        for village in villages:
            area = village.get("area_flooded_km2", 0.0)
            village_pop = village.get("population_affected")

            factors: Dict[str, float] = {}

            # Population factor: use village-level if available, else use area as proxy
            if village_pop is not None:
                factors["population"] = min(village_pop / max_pop, 1.0)
            elif affected_population and max_area > 0:
                # Proportional allocation by flooded area
                factors["population"] = min(area / max_area, 1.0)
            else:
                factors["population"] = 0.0

            # Buildings factor: use area as proxy (proportional to village area)
            factors["buildings"] = min(area / max_area, 1.0)

            # Roads factor: use area as proxy
            factors["roads"] = min(area / max_area, 1.0)

            # Weighted score
            score = sum(
                effective_weights.get(factor, 0.0) * value
                for factor, value in factors.items()
            )

            scored.append(
                {
                    "village_name": village.get("name", "Unknown"),
                    "priority_score": round(score, 4),
                    "rank": 0,  # Set after sorting
                    "contributing_factors": {k: round(v, 4) for k, v in factors.items()},
                }
            )

        # Sort by score descending and assign ranks
        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        for i, item in enumerate(scored):
            item["rank"] = i + 1

        return scored
