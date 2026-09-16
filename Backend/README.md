# SatQuery Backend — Phase 1 Prototype

SatQuery is an AI-powered, query-driven remote-sensing and GIS assistant for disaster analysis, with a flagship prototype for **flood extent and impact assessment**.

The system combines dual-satellite change detection with deterministic GIS datasets (village boundaries, population, building footprints, road networks, POIs, and DEM elevation) to generate verified flood polygons, exposure statistics, priority rankings, and candidate accessible sites for emergency response.

---

## End-to-End Workflow

```
Pre-Flood & Post-Flood Satellite Images (Sentinel GeoTIFFs)
                         ↓
             Image Pair Validation & Overlap Check
                         ↓
         Deterministic Flood Detection (NDWI / Differencing + Otsu)
                         ↓
                   Binary Flood Mask
                         ↓
              Geospatial Polygon Generation (GeoJSON WGS84)
                         ↓
              GIS Overlays & Multi-Layer Intersections
     ├── Village Boundaries  → Intersected Village Areas & Counts
     ├── Population Grids    → Modeled Population Exposure Estimates
     ├── Building Footprints → Submerged Building Counts
     ├── Road Networks       → Inundated Road Lengths (km)
     └── Elevation DEM       → Site Elevation Sampling
                         ↓
             Heuristic Impact & Priority Scoring
                         ↓
       Candidate Accessible Sites (Outside flood buffer, road & DEM aware)
                         ↓
       Interactive Leaflet Map & Grounded AI Assistant (No hallucinations)
```

---

## Directory Structure

```
Backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── health.py        # Service & DB health endpoints
│   │       │   ├── flood.py         # Full flood analysis pipeline & steps
│   │       │   └── chat.py          # Grounded AI assistant query endpoint
│   │       └── router.py            # API v1 router aggregator
│   ├── core/
│   │   └── config.py                # Environment settings, CORS, and data paths
│   ├── database/                    # SQLAlchemy & PostGIS session configuration
│   ├── schemas/
│   │   ├── health.py                # Health check schemas
│   │   ├── flood.py                 # Flood analysis, impact, & evacuation schemas
│   │   └── chat.py                  # AI assistant query & response schemas
│   ├── services/                    # Deterministic geospatial logic
│   │   ├── image_validation.py      # GeoTIFF metadata & overlap validator
│   │   ├── flood_detection.py       # NDWI & Differencing+Otsu change detector
│   │   ├── polygon_generation.py    # Raster mask to simplified GeoJSON polygons
│   │   ├── gis_repository.py        # File-based spatial layer & DEM loader
│   │   ├── gis_overlay.py           # Spatial intersection & road clipping engine
│   │   ├── exposure_analysis.py     # Multi-dataset impact & exposure metrics
│   │   ├── impact_scoring.py        # Heuristic multi-factor priority ranking
│   │   ├── evacuation.py            # Candidate accessible sites analysis
│   │   └── orchestration.py         # Grounded AI assistant orchestrator
│   ├── tools/                       # LLM callable function wrappers
│   │   ├── flood_tools.py
│   │   ├── gis_tools.py
│   │   ├── exposure_tools.py
│   │   ├── evacuation_tools.py
│   │   └── registry.py
│   └── main.py                      # FastAPI app entry point with lifespan
├── tests/
│   ├── test_health.py               # API health check tests
│   ├── test_database.py             # Database connectivity tests
│   ├── test_raster.py               # Raster validation & Otsu tests
│   ├── test_geospatial.py           # Polygonization, overlay & scoring tests
│   └── test_pipeline.py             # Full synthetic pipeline integration test
├── requirements.txt
└── README.md
```

---

## Important Disclaimers

- **Candidate Accessible Sites**: Facilities (schools, halls, civic centers) identified outside the flood boundary are **candidate accessible locations for on-ground verification only**. They are **NOT** guaranteed safe shelters or verified evacuation centers.
- **Population & Modeled Data**: Impact numbers and population figures are **modeled estimates** derived from spatial overlays of detected flood boundaries with available datasets.
- **Grounded AI Assistant**: The AI assistant strictly reports numbers returned by the deterministic analysis tools. It never invents coordinates, affected numbers, or GIS results.

---

## Getting Started

### 1. Install Backend Dependencies

From the `Backend` directory:
```powershell
cd C:\SatQuery\Backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Generate Sample Scenario Data (Optional)

Generate synthetic sample datasets (villages, buildings, roads, POIs) to test the pipeline immediately:
```powershell
cd C:\SatQuery
python scripts\generate_sample_data.py
```

### 3. Start the FastAPI Server

```powershell
cd C:\SatQuery\Backend
.\venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Interactive Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 4. Start the Frontend

In a separate terminal:
```powershell
cd C:\SatQuery\Frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Running Automated Tests

Run the complete test suite:
```powershell
cd C:\SatQuery\Backend
.\venv\Scripts\pytest tests/
```
