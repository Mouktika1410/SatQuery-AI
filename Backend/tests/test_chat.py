"""
Unit tests for AI Assistant orchestration and query grounding.
"""

from app.services.orchestration import AgentOrchestrationService


def get_mock_pipeline_result():
    return {
        "session_id": "test_session_123",
        "detection": {
            "success": True,
            "method_used": "differencing+otsu",
            "flooded_pixels": 9327,
            "total_pixels": 50000,
            "flood_percentage": 18.65,
            "flood_area_km2": 93.27,
        },
        "polygons": {
            "success": True,
            "polygon_count": 1,
            "total_area_km2": 93.27,
            "total_area_ha": 9327.0,
        },
        "impact": {
            "affected_villages": [
                {"name": "Village A", "area_flooded_km2": 45.2},
                {"name": "Village B", "area_flooded_km2": 28.1},
                {"name": "Village C", "area_flooded_km2": 19.97},
            ],
            "affected_population": 14250,
            "affected_buildings": 3120,
            "affected_road_length_km": 48.2,
            "data_availability": {
                "villages": True,
                "population": True,
                "buildings": True,
                "roads": True,
                "dem": True,
            },
        },
        "priority_scores": [
            {"rank": 1, "village_name": "Village A", "priority_score": 0.85},
            {"rank": 2, "village_name": "Village B", "priority_score": 0.62},
            {"rank": 3, "village_name": "Village C", "priority_score": 0.41},
        ],
        "evacuation": {
            "total_found": 2,
            "candidates": [
                {
                    "name": "School A",
                    "type": "school",
                    "distance_to_flood_km": 1.2,
                    "elevation_m": 14.5,
                },
                {
                    "name": "Community Hall B",
                    "type": "government",
                    "distance_to_flood_km": 2.5,
                    "elevation_m": 18.2,
                },
            ],
            "disclaimer": "Candidate accessible sites identified for on-ground verification only.",
        },
    }


def test_flooded_area_query():
    svc = AgentOrchestrationService()
    res = svc.answer_query("What is the flooded area?", get_mock_pipeline_result())
    assert "93.27 km²" in res["answer"]
    assert len(res["data_used"]) > 0


def test_affected_population_query():
    svc = AgentOrchestrationService()
    res = svc.answer_query("How many people are affected?", get_mock_pipeline_result())
    assert "14,250" in res["answer"]


def test_affected_villages_query():
    svc = AgentOrchestrationService()
    res = svc.answer_query("Which villages are affected?", get_mock_pipeline_result())
    assert "Village A" in res["answer"]
    assert "3 village(s)" in res["answer"]


def test_affected_buildings_query():
    svc = AgentOrchestrationService()
    res = svc.answer_query("How many buildings are affected?", get_mock_pipeline_result())
    assert "3,120" in res["answer"]


def test_evacuation_query():
    svc = AgentOrchestrationService()
    res = svc.answer_query("Show the candidate evacuation locations.", get_mock_pipeline_result())
    assert "School A" in res["answer"]
    assert "Candidate accessible sites" in res["answer"]


def test_priority_analysis_query():
    svc = AgentOrchestrationService()
    res = svc.answer_query("What is the priority analysis?", get_mock_pipeline_result())
    assert "Village A" in res["answer"]
    assert "decision-support" in res["answer"]


if __name__ == "__main__":
    test_flooded_area_query()
    test_affected_population_query()
    test_affected_villages_query()
    test_affected_buildings_query()
    test_evacuation_query()
    test_priority_analysis_query()
    print("All AI Assistant chat tests passed!")
