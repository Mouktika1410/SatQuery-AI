"""
AI Agent Orchestration Service.

Routes natural language queries to deterministic analysis results.
Enforces strict rule: The assistant only describes metrics that were
actually computed by the analysis pipeline. It never invents numbers.

When GEMINI_API_KEY is configured, LLM function calling can be added.
When it is not configured, a rule-based pattern-matching fallback is used.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "This information is derived from deterministic geospatial analysis. "
    "Results should be verified with ground surveys before operational use."
)

_NO_RESULTS_ANSWER = (
    "No analysis results are available yet. "
    "Please upload two georeferenced GeoTIFF images and run the flood analysis first."
)


class AgentOrchestrationService:
    """
    Orchestrator for the AI-powered query interface.

    Routes user questions to pre-computed deterministic results.
    Strict architectural rule: this service never invents metrics.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self.ai_available = api_key is not None

    def answer_query(
        self,
        question: str,
        pipeline_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Answer a natural language question using computed pipeline results.

        Args:
            question: User's natural language question
            pipeline_result: The full PipelineResult dict from a prior analysis run

        Returns:
            Dict matching ChatResponse schema.
        """
        if not pipeline_result:
            return {
                "answer": _NO_RESULTS_ANSWER,
                "data_used": [],
                "ai_powered": False,
                "disclaimer": _DISCLAIMER,
            }

        q = question.lower().strip()
        answer, data_used = self._rule_based_answer(q, pipeline_result)

        if answer:
            return {
                "answer": f"Based on the analysis results: {answer}",
                "data_used": data_used,
                "ai_powered": False,
                "disclaimer": _DISCLAIMER,
            }

        # No pattern matched
        if self.ai_available:
            return {
                "answer": (
                    "Your question was not matched by the built-in query patterns. "
                    "LLM integration is configured (API key present) but full function-calling "
                    "is not yet enabled in this version. "
                    "You can ask about: flooded area, affected villages, affected buildings, "
                    "affected population, affected roads, priority scores, or evacuation candidates."
                ),
                "data_used": [],
                "ai_powered": False,
                "disclaimer": _DISCLAIMER,
            }

        available_topics = (
            "flooded area, affected villages, affected buildings, affected population, "
            "affected roads, priority scores, evacuation candidates"
        )
        return {
            "answer": (
                f"I can answer questions about: {available_topics}. "
                "Try rephrasing your question, or set a GEMINI_API_KEY to enable full LLM assistance."
            ),
            "data_used": [],
            "ai_powered": False,
            "disclaimer": _DISCLAIMER,
        }

    def _rule_based_answer(
        self, question: str, result: Dict[str, Any]
    ) -> tuple[Optional[str], List[str]]:
        """
        Pattern-matching fallback that queries computed results.
        Returns (answer_text | None, data_sources_used).
        """
        detection = result.get("detection") or {}
        polygons = result.get("polygons") or {}
        impact = result.get("impact") or {}
        priority = result.get("priority_scores") or []
        evacuation = result.get("evacuation") or {}

        # --- Flooded area ---
        if any(kw in question for kw in ["flood area", "flooded area", "how much", "area flooded", "km2", "hectare", "size"]):
            area_km2 = polygons.get("total_area_km2") or detection.get("flood_area_km2") or 0.0
            area_ha = polygons.get("total_area_ha") or (area_km2 * 100)
            pct = detection.get("flood_percentage", 0.0)
            return (
                f"the detected flooded area is approximately {area_km2:.2f} km² "
                f"({area_ha:.1f} hectares), representing {pct:.2f}% of the analysed imagery extent.",
                ["detection.flood_area_km2", "polygons.total_area_km2"],
            )

        # --- Affected villages ---
        if any(kw in question for kw in ["village", "villages", "settlement", "admin", "which area"]):
            villages = impact.get("affected_villages", [])
            if not villages:
                avail = impact.get("data_availability", {}).get("villages", False)
                if not avail:
                    return (
                        "no village boundary dataset was loaded. "
                        "Place a GeoJSON file in data/boundaries/ to enable village-level analysis.",
                        [],
                    )
                return "no villages were found to intersect the detected flood extent.", ["impact.affected_villages"]
            names = [v["name"] for v in villages[:10]]
            count = len(villages)
            most = villages[0]
            return (
                f"{count} village(s) are intersected by the flood. "
                f"Most affected: {most['name']} ({most['area_flooded_km2']:.2f} km² flooded). "
                f"All affected: {', '.join(names)}.",
                ["impact.affected_villages"],
            )

        # --- Affected population ---
        if any(kw in question for kw in ["population", "people", "resident", "how many people", "inhabitants"]):
            pop = impact.get("affected_population")
            avail = impact.get("data_availability", {}).get("population", False)
            if not avail:
                return (
                    "no population dataset was loaded. "
                    "Place a population GeoJSON or raster in data/population/ to enable this metric.",
                    [],
                )
            if pop is None:
                return "affected population could not be calculated from the available data.", []
            return (
                f"approximately {pop:,} people are estimated to be in flood-affected areas "
                f"based on population data intersected with the flood boundary.",
                ["impact.affected_population"],
            )

        # --- Affected buildings ---
        if any(kw in question for kw in ["building", "buildings", "structure", "property", "house"]):
            bldg = impact.get("affected_buildings")
            avail = impact.get("data_availability", {}).get("buildings", False)
            if not avail:
                return (
                    "no building footprint dataset was loaded. "
                    "Place a building GeoJSON in data/buildings/ to enable this metric.",
                    [],
                )
            if bldg is None:
                return "affected building count could not be calculated.", []
            return (
                f"{bldg:,} building footprint(s) intersect the detected flood extent.",
                ["impact.affected_buildings"],
            )

        # --- Affected roads ---
        if any(kw in question for kw in ["road", "roads", "highway", "street", "infrastructure"]):
            road_km = impact.get("affected_road_length_km")
            avail = impact.get("data_availability", {}).get("roads", False)
            if not avail:
                return (
                    "no road network dataset was loaded. "
                    "Place a roads GeoJSON in data/roads/ to enable this metric.",
                    [],
                )
            if road_km is None:
                return "affected road length could not be calculated.", []
            return (
                f"approximately {road_km:.2f} km of road network falls within the flood extent.",
                ["impact.affected_road_length_km"],
            )

        # --- Priority / most affected ---
        if any(kw in question for kw in ["priority", "most affected", "worst", "urgent", "rank"]):
            if not priority:
                return (
                    "priority scores could not be computed "
                    "(no village data or no affected villages found).",
                    [],
                )
            top = priority[:3]
            lines = [f"Rank {p['rank']}: {p['village_name']} (score {p['priority_score']:.3f})" for p in top]
            return (
                "the top priority areas (heuristic decision-support scores — not validated predictions) are: "
                + "; ".join(lines)
                + ". These scores are based on normalized flooded area, population, and infrastructure factors.",
                ["priority_scores"],
            )

        # --- Evacuation candidates ---
        if any(kw in question for kw in ["evacuation", "shelter", "safe", "candidate", "poi", "site", "school"]):
            candidates = evacuation.get("candidates", [])
            total = evacuation.get("total_found", 0)
            if total == 0:
                reason = evacuation.get("filtered_reason", "No candidates found.")
                return (
                    f"no candidate accessible sites were identified. Reason: {reason} "
                    "Note: Candidates require a POI dataset in data/pois/.",
                    [],
                )
            top_sites = candidates[:5]
            site_lines = [
                f"{s['name']} ({s['type']}, {s['distance_to_flood_km'] or 'N/A'} km from flood)"
                for s in top_sites
            ]
            return (
                f"{total} candidate accessible site(s) were identified outside the flood boundary: "
                + "; ".join(site_lines)
                + ". IMPORTANT: " + evacuation.get("disclaimer", _DISCLAIMER),
                ["evacuation.candidates"],
            )

        # --- Polygon count ---
        if any(kw in question for kw in ["polygon", "patch", "how many flood"]):
            count = polygons.get("polygon_count", 0)
            return (
                f"the flood mask was vectorized into {count} separate polygon feature(s).",
                ["polygons.polygon_count"],
            )

        return None, []
