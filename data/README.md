# SatQuery — Data Directory

This directory holds all geospatial input data for Phase 1 analysis.

**No large datasets are bundled with this repository.**
Place datasets in the appropriate subdirectory before running analysis.

---

## Directory Structure

```
data/
├── input/          ← Uploaded GeoTIFF images (written by the backend at runtime)
├── output/         ← Generated flood masks and intermediate outputs
├── boundaries/     ← Village / administrative boundary polygons
├── population/     ← Population grid or polygon data
├── buildings/      ← Building footprint polygons
├── roads/          ← Road network line features
├── pois/           ← Points of interest (schools, community halls, shelters…)
└── dem/            ← Digital elevation model rasters (optional, for elevation filtering)
```

---

## Supported Formats

| Layer        | Accepted Formats           | Notes                              |
|--------------|----------------------------|------------------------------------|
| boundaries   | GeoJSON, Shapefile, GeoPackage | Must have a `name` column        |
| population   | GeoJSON, Shapefile, GeoPackage | Must have a `population` column  |
| buildings    | GeoJSON, Shapefile, GeoPackage | Point or polygon footprints      |
| roads        | GeoJSON, Shapefile, GeoPackage | LineString or MultiLineString    |
| pois         | GeoJSON, Shapefile, GeoPackage | Must have `name` and `type`/`amenity` columns |
| dem          | GeoTIFF (float32)          | Elevation in metres                |

All vector files must use WGS84 (EPSG:4326) or include a CRS definition.
The backend will reproject to match the flood image CRS automatically.

---

## Recommended Data Sources (Public, Free)

| Dataset                | Source                                                        |
|------------------------|---------------------------------------------------------------|
| Admin boundaries       | [GADM](https://gadm.org/) — gadm.org                        |
| Population             | [WorldPop](https://www.worldpop.org/) — worldpop.org        |
| Buildings              | [Microsoft Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints) |
| Roads                  | [OpenStreetMap / Geofabrik](https://download.geofabrik.de/) |
| POIs                   | OpenStreetMap (schools, hospitals, community centers)         |
| DEM                    | [SRTM / NASA Earthdata](https://earthdata.nasa.gov/)        |
| Sentinel-1/2 imagery   | [Copernicus Open Access Hub](https://scihub.copernicus.eu/) |

---

## Important Notes

- The backend will check `data/boundaries/`, `data/buildings/`, etc. on startup and log which layers are available.
- Missing optional datasets will not cause errors — the corresponding impact metrics will report `N/A`.
- Do NOT place imagery larger than the `MAX_UPLOAD_SIZE_MB` limit directly in `data/input/`. Use the API upload endpoint instead.
- Large raster files (`.tif`, `.tiff`, `*.shp`, etc.) are excluded from Git via `.gitignore`.
