"""
GIS Repository — File-Based Geospatial Data Provider.

Abstracts loading of local spatial datasets from the data/ directory.
Supports both vector layers (.geojson, .gpkg, .shp) and raster layers (DEM GeoTIFFs).
This clean interface can be swapped out for a PostGIS-backed provider in Phase 2.
"""

import os
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

try:
    import rasterio
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

# Map logical layer names to subdirectory paths
_LAYER_DIRS = {
    "villages": "boundaries",
    "population": "population",
    "buildings": "buildings",
    "roads": "roads",
    "pois": "pois",
    "dem": "dem",
}

# Supported spatial vector file extensions
_VECTOR_EXTENSIONS = [".geojson", ".gpkg", ".shp", ".json"]

# Supported spatial raster file extensions
_RASTER_EXTENSIONS = [".tif", ".tiff", ".geotiff", ".img"]


class GISRepository:
    """
    File-based geospatial data loader for SatQuery.

    Loads GeoJSON, GeoPackage, or Shapefile vector layers, as well as DEM GeoTIFF rasters
    from the project data/ directory structure.
    """

    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir

    def load_layer(self, layer_type: str) -> Optional[Any]:
        """
        Load a named vector spatial layer from the file system.

        Args:
            layer_type: One of 'villages', 'population', 'buildings',
                        'roads', 'pois'.

        Returns:
            GeoDataFrame or None if no file is found or geopandas is missing.
        """
        if not GEOPANDAS_AVAILABLE:
            logger.warning("geopandas is not installed — cannot load vector GIS layers.")
            return None

        if layer_type not in _LAYER_DIRS:
            logger.warning("Unknown layer type: %s", layer_type)
            return None

        subdir = _LAYER_DIRS[layer_type]
        directory = os.path.join(self.data_dir, subdir)

        file_path = self._find_file(directory, _VECTOR_EXTENSIONS)
        if not file_path:
            logger.info("No vector spatial file found for layer '%s' in %s", layer_type, directory)
            return None

        try:
            gdf = gpd.read_file(file_path)
            logger.info(
                "Loaded vector layer '%s' from %s (%d features)",
                layer_type,
                file_path,
                len(gdf),
            )
            return gdf
        except Exception as exc:
            logger.error(
                "Failed to load vector layer '%s' from %s: %s", layer_type, file_path, exc
            )
            return None

    def get_dem_path(self) -> Optional[str]:
        """
        Find and return the file path to a DEM GeoTIFF raster in data/dem/.
        """
        directory = os.path.join(self.data_dir, _LAYER_DIRS.get("dem", "dem"))
        return self._find_file(directory, _RASTER_EXTENSIONS)

    def sample_elevation(self, lat: float, lon: float) -> Optional[float]:
        """
        Sample elevation in meters at (lat, lon) from the available DEM raster.
        Returns None if no DEM raster is present or sampling fails.
        """
        if not RASTERIO_AVAILABLE:
            return None

        dem_path = self.get_dem_path()
        if not dem_path:
            return None

        try:
            with rasterio.open(dem_path) as ds:
                # Sample point (lon, lat in WGS84)
                from pyproj import Transformer
                if ds.crs and not ds.crs.is_geographic:
                    transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
                    x, y = transformer.transform(lon, lat)
                else:
                    x, y = lon, lat

                row, col = ds.index(x, y)
                if 0 <= row < ds.height and 0 <= col < ds.width:
                    window = rasterio.windows.Window(col, row, 1, 1)
                    val = ds.read(1, window=window)[0, 0]
                    if ds.nodata is not None and val == ds.nodata:
                        return None
                    return round(float(val), 1)
        except Exception as exc:
            logger.debug("DEM elevation sampling failed at (%f, %f): %s", lat, lon, exc)

        return None

    def available_layers(self) -> Dict[str, bool]:
        """
        Return a dict of which data layers are available in the data directory.
        """
        result: Dict[str, bool] = {}
        for layer_type, subdir in _LAYER_DIRS.items():
            directory = os.path.join(self.data_dir, subdir)
            if layer_type == "dem":
                result[layer_type] = self._find_file(directory, _RASTER_EXTENSIONS) is not None
            else:
                result[layer_type] = self._find_file(directory, _VECTOR_EXTENSIONS) is not None
        return result

    def _find_file(self, directory: str, extensions: list[str]) -> Optional[str]:
        """
        Scan a directory for the first file matching given extensions.
        """
        if not os.path.isdir(directory):
            return None
        try:
            for ext in extensions:
                for fname in os.listdir(directory):
                    if fname.lower().endswith(ext) and not fname.startswith("."):
                        return os.path.join(directory, fname)
        except OSError as exc:
            logger.error("Error scanning directory %s: %s", directory, exc)
        return None
