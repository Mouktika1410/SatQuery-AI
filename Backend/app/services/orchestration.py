"""
AI Agent Orchestration Service.

Routes natural language queries to deterministic analysis results.
Enforces strict rule: The assistant only describes metrics that were
actually computed by the analysis pipeline. It never invents numbers.

When GEMINI_API_KEY is configured, Gemini generative LLM integration is used.
When GEMINI_API_KEY is missing or API fails, an enhanced rule-based pattern matching fallback is used.
"""

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "This information is derived from deterministic geospatial analysis. "
    "Results should be verified with ground surveys before operational use."
)

_EVAC_DISCLAIMER = (
    "Candidate accessible sites identified for on-ground verification only. "
    "These locations are NOT guaranteed safe shelters or verified evacuation centers."
)

_PRIORITY_DISCLAIMER = (
    "Heuristic decision-support score based on available normalized geospatial factors. "
    "This is a decision-support metric, NOT a machine-learning prediction."
)

_NO_RESULTS_ANSWER = (
    "No analysis results are available yet. "
    "Please upload two georeferenced GeoTIFF images and run the flood analysis first."
)

_SYSTEM_INSTRUCTION = f"""
You are SatQuery's AI flood disaster analysis assistant.
Your role is to answer user questions about flood extent, impacted population, submerged buildings, inundated roads, village priority rankings, candidate evacuation locations, elevation, and GIS layer availability.

CRITICAL GROUNDING RULES:
1. Answer ONLY using the exact data provided in the analysis results JSON. NEVER invent geographic measurements, village names, building counts, population numbers, scores, or evacuation locations.
2. Identify all flood and impact metrics as modeled or computed estimates.
3. For candidate evacuation locations, ALWAYS state: "{_EVAC_DISCLAIMER}".
4. For priority scores, ALWAYS state: "{_PRIORITY_DISCLAIMER}".
5. If a requested metric or GIS layer was not available in the analysis, explicitly state that the data layer was not loaded.
6. Keep responses clear, professional, concise, and structured.
"""


class AgentOrchestrationService:
    """
    Orchestrator for the AI-powered query interface.

    Routes user questions to pre-computed deterministic results.
    Strict architectural rule: this service never invents metrics.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        key = api_key
        if not key or not key.strip():
            from app.core.config import settings
            key = settings.GEMINI_API_KEY
        if key and key.strip():
            self.api_key = key.strip()
            self.ai_available = True
        else:
            self.api_key = None
            self.ai_available = False

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

        # Try Gemini LLM if API key is present
        if self.ai_available:
            llm_response = self._query_gemini_llm(q, pipeline_result)
            if llm_response:
                return {
                    "answer": llm_response["answer"],
                    "data_used": llm_response["data_used"],
                    "ai_powered": True,
                    "disclaimer": _DISCLAIMER,
                }

        # Deterministic rule-based fallback
        answer, data_used = self._rule_based_answer(q, pipeline_result)
        if answer:
            return {
                "answer": f"Based on the analysis results: {answer}",
                "data_used": data_used,
                "ai_powered": False,
                "disclaimer": _DISCLAIMER,
            }

        # Question unrecognized and no LLM response
        available_topics = (
            "flooded area, affected villages, affected buildings, affected population, "
            "affected roads, priority rankings, candidate evacuation locations, DEM elevation, data layer availability"
        )
        msg = (
            f"I can answer questions about: {available_topics}. "
            "Try rephrasing your question."
        )
        if not self.ai_available:
            msg += " Set the GEMINI_API_KEY environment variable to enable full generative AI reasoning."

        return {
            "answer": msg,
            "data_used": [],
            "ai_powered": False,
            "disclaimer": _DISCLAIMER,
        }

    def _query_gemini_llm(
        self, question: str, result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Call Gemini REST API with structured session context.
        """
        if not self.api_key:
            return None

        # Build clean JSON summary context
        summary_context = {
            "detection": {
                "flooded_area_km2": result.get("polygons", {}).get("total_area_km2") or result.get("detection", {}).get("flood_area_km2"),
                "flood_percentage": result.get("detection", {}).get("flood_percentage"),
                "detection_method": result.get("detection", {}).get("method_used"),
                "polygon_count": result.get("polygons", {}).get("polygon_count"),
            },
            "impact": {
                "affected_population": result.get("impact", {}).get("affected_population"),
                "affected_buildings": result.get("impact", {}).get("affected_buildings"),
                "affected_road_length_km": result.get("impact", {}).get("affected_road_length_km"),
                "affected_villages": result.get("impact", {}).get("affected_villages"),
                "data_availability": result.get("impact", {}).get("data_availability"),
            },
            "priority_scores": result.get("priority_scores"),
            "evacuation_candidates": result.get("evacuation"),
        }

        prompt = (
            f"Analysis Results JSON:\n{json.dumps(summary_context, indent=2)}\n\n"
            f"User Question: {question}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
        }

        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    text_parts = candidates[0].get("content", {}).get("parts", [])
                    if text_parts:
                        ans_text = text_parts[0].get("text", "").strip()
                        return {
                            "answer": ans_text,
                            "data_used": ["pipeline_result_context"],
                        }
        except Exception as e:
            logger.warning(f"Gemini LLM call encountered error: {e}. Falling back to deterministic rules.")
            return None

        return None

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
        availability = impact.get("data_availability") or {}

        # --- Flooded area ---
        if any(kw in question for kw in ["flood area", "flooded area", "how much", "area flooded", "km2", "hectare", "extent"]):
            area_km2 = polygons.get("total_area_km2") or detection.get("flood_area_km2") or 0.0
            area_ha = polygons.get("total_area_ha") or (area_km2 * 100)
            pct = detection.get("flood_percentage", 0.0)
            poly_cnt = polygons.get("polygon_count", 1)
            method = detection.get("method_used", "auto")
            return (
                f"the detected flooded area is approximately {area_km2:.2f} km² "
                f"({area_ha:.1f} hectares), representing {pct:.2f}% of the imagery extent. "
                f"Detected using {method} and vectorized into {poly_cnt} flood polygon(s).",
                ["detection.flood_area_km2", "polygons.total_area_km2"],
            )

        # --- Affected population ---
        if any(kw in question for kw in ["population", "people", "resident", "how many people", "inhabitants"]):
            pop = impact.get("affected_population")
            if not availability.get("population", False):
                return (
                    "population grid GIS dataset was not available for this analysis. "
                    "Add population data to data/population/ to enable population impact estimates.",
                    [],
                )
            if pop is None:
                return "affected population could not be calculated from the available dataset.", []
            return (
                f"approximately {pop:,} people are estimated to be in flood-affected areas "
                f"based on modeled spatial population data intersected with the flood boundary.",
                ["impact.affected_population"],
            )

        # --- Affected villages ---
        if any(kw in question for kw in ["village", "villages", "settlement", "admin", "which area"]):
            villages = impact.get("affected_villages", [])
            if not villages:
                if not availability.get("villages", False):
                    return (
                        "no village boundary GIS layer was loaded for this analysis.",
                        [],
                    )
                return "no mapped village boundaries intersect the detected flood extent.", ["impact.affected_villages"]
            names = [v["name"] for v in villages]
            count = len(villages)
            most = max(villages, key=lambda x: x.get("area_flooded_km2", 0.0))
            return (
                f"{count} village(s) are intersected by the flood boundary: {', '.join(names)}. "
                f"Most affected: {most['name']} with {most['area_flooded_km2']:.2f} km² flooded.",
                ["impact.affected_villages"],
            )

        # --- Affected buildings ---
        if any(kw in question for kw in ["building", "buildings", "structure", "property", "house"]):
            bldg = impact.get("affected_buildings")
            if not availability.get("buildings", False):
                return (
                    "no building footprint GIS dataset was loaded for this analysis.",
                    [],
                )
            if bldg is None:
                return "affected building count could not be calculated.", []
            return (
                f"approximately {bldg:,} building footprint(s) intersect the detected flood extent.",
                ["impact.affected_buildings"],
            )

        # --- Affected roads ---
        if any(kw in question for kw in ["road", "roads", "highway", "street", "infrastructure", "inundated road"]):
            road_km = impact.get("affected_road_length_km")
            if not availability.get("roads", False):
                return (
                    "no road network GIS dataset was loaded for this analysis.",
                    [],
                )
            if road_km is None:
                return "inundated road length could not be calculated.", []
            return (
                f"approximately {road_km:.2f} km of road network falls within the detected flood boundary.",
                ["impact.affected_road_length_km"],
            )

        # --- Priority / ranking / highest priority ---
        if any(kw in question for kw in ["priority", "most affected", "worst", "urgent", "rank"]):
            if not priority:
                return (
                    "priority scores were not computed (no village boundaries or no affected villages found).",
                    [],
                )
            top = priority[:3]
            lines = [f"Rank {p['rank']}: {p['village_name']} (score: {p['priority_score']:.3f})" for p in top]
            return (
                "the top priority areas are: "
                + "; ".join(lines)
                + f". Note: {_PRIORITY_DISCLAIMER}",
                ["priority_scores"],
            )

        # --- Evacuation candidates / sites ---
        if any(kw in question for kw in ["evacuation", "shelter", "safe", "candidate", "poi", "site", "school", "facility"]):
            candidates = evacuation.get("candidates", [])
            total = evacuation.get("total_found", 0)
            if total == 0:
                reason = evacuation.get("filtered_reason", "No candidates found.")
                return (
                    f"no candidate accessible sites were identified outside the flood zone. Reason: {reason}",
                    [],
                )
            site_lines = []
            for s in candidates[:5]:
                dist_str = f"{s['distance_to_flood_km']:.2f} km from flood" if s.get("distance_to_flood_km") is not None else "outside flood"
                elev_str = f", DEM elevation: {s['elevation_m']:.1f} m" if s.get("elevation_m") is not None else ""
                site_lines.append(f"🏫 {s['name']} ({s['type']}, {dist_str}{elev_str})")
            return (
                f"{total} candidate accessible site(s) located outside the flood boundary: "
                + "; ".join(site_lines)
                + f". Operational Caution: {_EVAC_DISCLAIMER}",
                ["evacuation.candidates"],
            )

        # --- Elevation ---
        if any(kw in question for kw in ["elevation", "altitude", "height", "dem"]):
            candidates = evacuation.get("candidates", [])
            elev_values = [c["elevation_m"] for c in candidates if c.get("elevation_m") is not None]
            if not availability.get("dem", False) or not elev_values:
                return (
                    "DEM elevation data layer was not available or not linked for this session.",
                    [],
                )
            elev_str = ", ".join([f"{c['name']}: {c['elevation_m']:.1f} m" for c in candidates[:4]])
            return (
                f"candidate facility elevations range from {min(elev_values):.1f} m to {max(elev_values):.1f} m above sea level ({elev_str}).",
                ["evacuation.candidates.elevation_m"],
            )

        # --- Data layer availability ---
        if any(kw in question for kw in ["data layer", "availability", "available layer", "dataset", "layers loaded"]):
            if not availability:
                return "data layer availability status was not recorded for this analysis session.", []
            status_items = [f"{k.capitalize()}: {'Available' if v else 'Missing'}" for k, v in availability.items()]
            return (
                "GIS data layer availability status for this analysis session: " + "; ".join(status_items) + ".",
                ["impact.data_availability"],
            )

        # --- Polygon count ---
        if any(kw in question for kw in ["polygon", "patch", "how many flood"]):
            count = polygons.get("polygon_count", 0)
            return (
                f"the detected flood mask was vectorized into {count} polygon feature(s).",
                ["polygons.polygon_count"],
            )

        # --- VLM Visual Comparison ---
        if any(kw in question for kw in ["vlm", "visual change", "visual comparison", "before after", "visual evidence", "satellite visual"]):
            vlm = result.get("vlm_analysis") or {}
            comp = vlm.get("comparison", "VLM visual comparison is not available for this session.")
            return (
                f"VLM Satellite Visual Analysis: {comp}",
                ["vlm_analysis.comparison"],
            )

        return None, []

    def generate_visual_comparison(
        self, pre_path: str, post_path: str
    ) -> Dict[str, Any]:
        """
        Generate a qualitative visual comparison of pre and post satellite images using Gemini Multimodal VLM.

        Args:
            pre_path: File path to pre-flood GeoTIFF
            post_path: File path to post-flood GeoTIFF

        Returns:
            Dict matching VLMAnalysisResult schema.
        """
        disclaimer = (
            "Visual comparison performed by Gemini Multimodal VLM. "
            "Qualitative visual description separate from quantitative GIS measurements."
        )

        if not self.ai_available or not self.api_key:
            return {
                "available": False,
                "comparison": "VLM visual comparison is unavailable. Set GEMINI_API_KEY environment variable to enable satellite image visual change analysis.",
                "disclaimer": disclaimer,
            }

        pre_b64 = _convert_geotiff_to_jpeg_b64(pre_path)
        post_b64 = _convert_geotiff_to_jpeg_b64(post_path)

        if not pre_b64 or not post_b64:
            return {
                "available": False,
                "comparison": "VLM visual comparison unavailable: Satellite image conversion failed or files were unreadable.",
                "disclaimer": disclaimer,
            }

        prompt = (
            "You are analyzing a pair of satellite images taken BEFORE and AFTER a potential flood event.\n"
            "Image 1: Pre-event satellite image.\n"
            "Image 2: Post-event satellite image.\n\n"
            "Provide a short qualitative visual comparison answering:\n"
            "1. What visual changes are visible between before and after?\n"
            "2. Is there visible evidence of increased surface water or flooding?\n"
            "3. Which areas show notable visual change?\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Do NOT calculate or estimate numerical flood area (km²), population, building counts, or priority scores.\n"
            "- Focus strictly on qualitative visual observations (e.g. darkening of soil, expanding water bodies, submerged vegetation, color changes).\n"
            "- Keep response concise, structured, and under 200 words."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": pre_b64,
                            }
                        },
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": post_b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
        }

        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    text_parts = candidates[0].get("content", {}).get("parts", [])
                    if text_parts:
                        ans_text = text_parts[0].get("text", "").strip()
                        return {
                            "available": True,
                            "comparison": ans_text,
                            "disclaimer": disclaimer,
                        }
        except Exception as e:
            logger.warning(f"Gemini VLM call encountered error: {e}")
            return {
                "available": False,
                "comparison": f"VLM visual comparison request failed: {e}",
                "disclaimer": disclaimer,
            }

        return {
            "available": False,
            "comparison": "VLM visual comparison produced no output.",
            "disclaimer": disclaimer,
        }


def _convert_geotiff_to_jpeg_b64(file_path: str, max_size: int = 512) -> Optional[str]:
    """Convert GeoTIFF image to base64 JPEG string for Gemini VLM."""
    import base64
    import io
    import os

    if not file_path or not os.path.exists(file_path):
        return None
    try:
        import numpy as np
        import rasterio
        from PIL import Image

        with rasterio.open(file_path) as ds:
            cnt = ds.count
            if cnt >= 3:
                b1 = ds.read(1)
                b2 = ds.read(2)
                b3 = ds.read(3)
                img_arr = np.dstack((b1, b2, b3))
            else:
                b1 = ds.read(1)
                img_arr = np.dstack((b1, b1, b1))

            # Convert MaskedArray to standard numpy ndarray and capture mask safely
            is_masked = isinstance(img_arr, np.ma.MaskedArray)
            if is_masked:
                raw_mask = img_arr.mask
                if raw_mask is not np.ma.nomask and raw_mask is not False and np.any(raw_mask):
                    ma_mask = np.asarray(raw_mask, dtype=bool)
                else:
                    ma_mask = None
                img_arr = np.asarray(np.ma.getdata(img_arr))
            else:
                ma_mask = None

            # Build valid mask excluding nodata, NaN, Inf, and MaskedArray mask
            valid_mask = np.isfinite(img_arr)
            if ds.nodata is not None:
                valid_mask = valid_mask & (img_arr != ds.nodata)
            if ma_mask is not None:
                valid_mask = valid_mask & (~ma_mask)

            valid_mask = np.asarray(valid_mask, dtype=bool)

            if np.any(valid_mask):
                valid_vals = img_arr[valid_mask]
                min_val = float(np.min(valid_vals))
                max_val = float(np.max(valid_vals))
            else:
                min_val, max_val = 0.0, 1.0

            clean_arr = np.asarray(np.where(valid_mask, img_arr, min_val))

            if max_val > min_val:
                scaled = (clean_arr - min_val) / (max_val - min_val) * 255.0
            else:
                scaled = np.zeros_like(clean_arr)

            img_norm = np.asarray(
                np.clip(np.nan_to_num(scaled, nan=0.0, posinf=255.0, neginf=0.0), 0, 255),
                dtype=np.uint8,
            )

            pil_img = Image.fromarray(img_norm)
            pil_img.thumbnail((max_size, max_size))

            buffer = io.BytesIO()
            pil_img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        logger.warning(f"GeoTIFF conversion for VLM failed ({file_path}): {e}")
        return None


