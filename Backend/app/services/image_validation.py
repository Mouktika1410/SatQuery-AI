"""
Image Validation Service.

Validates GeoTIFF files for geospatial completeness and pair-compatibility.
All rasterio imports are wrapped to provide clear error messages when the
package is not yet installed.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Rasterio import guard
# ---------------------------------------------------------------------------
try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_gcps
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False


def inspect_sar_properties(ds: Any) -> Tuple[bool, Optional[str], List[str], Optional[bool]]:
    """
    Inspect a rasterio dataset to detect Sentinel-1 SAR characteristics.
    Returns (is_sar, sensor_name, polarizations, is_db).
    """
    pols: List[str] = []
    is_sar = False
    sensor = None
    is_db = None

    # 1. Band descriptions (e.g. ('VV',), ('Sigma0_VV_db',), ('Gamma0_VH',))
    if ds.descriptions:
        for desc in ds.descriptions:
            if desc:
                d_upper = desc.upper()
                for p in ["VV", "VH", "HH", "HV"]:
                    if p in d_upper and p not in pols:
                        pols.append(p)
                if any(k in d_upper for k in ["SIGMA0", "GAMMA0", "SAR", "SENTINEL-1", "S1", "BACKSCATTER", "DB"]):
                    is_sar = True

    # 2. Tags & metadata
    try:
        tags = ds.tags()
        tag_str = " ".join(f"{k}:{v}" for k, v in tags.items()).upper()
        if any(k in tag_str for k in ["SENTINEL-1", "S1A", "S1B", "SAR", "C-SAR", "IW_GRD", "IW", "EW"]):
            is_sar = True
            sensor = "Sentinel-1 SAR"
        for p in ["VV", "VH", "HH", "HV"]:
            if p in tag_str and p not in pols:
                pols.append(p)
    except Exception:
        pass

    # 3. Filename
    fname = os.path.basename(getattr(ds, "name", "") or "").upper()
    if any(k in fname for k in ["S1A_", "S1B_", "SENTINEL1", "SENTINEL-1", "S1_"]):
        is_sar = True
        sensor = "Sentinel-1 SAR"
    for p in ["VV", "VH", "HH", "HV"]:
        if f"_{p}" in fname or f"-{p}" in fname or f".{p}." in fname or f"_{p}." in fname:
            if p not in pols:
                pols.append(p)

    # 4. Pixel dynamic range check for 1-2 band rasters
    if ds.count <= 2:
        if pols:
            is_sar = True
        try:
            import numpy as np
            sub_h = min(ds.height, 32)
            sub_w = min(ds.width, 32)
            sample = ds.read(1, out_shape=(sub_h, sub_w)).astype(np.float32)
            valid = np.isfinite(sample)
            if ds.nodata is not None:
                valid &= (sample != ds.nodata)
            if np.any(valid):
                valid_vals = sample[valid]
                v_min = float(np.min(valid_vals))
                v_max = float(np.max(valid_vals))
                v_med = float(np.median(valid_vals))
                # Decibel values: backscatter is typically between -35 dB and +5 dB (negative median)
                if -50.0 <= v_min <= -1.0 and v_med < 0.0 and v_max <= 25.0:
                    is_sar = True
                    is_db = True
                    if not pols:
                        pols.append("VV")  # Standard default polarization
                elif v_min >= 0.0 and v_max > 0.0 and is_sar:
                    is_db = False
        except Exception:
            pass

    if is_sar and not sensor:
        sensor = "Sentinel-1 SAR"

    return is_sar, sensor, pols, is_db


def validate_geotiff(file_path: str) -> Dict[str, Any]:
    """
    Inspect a GeoTIFF file and return its spatial metadata.

    Returns a dict with 'valid' key. If 'valid' is False, 'error' explains why.
    """
    result: Dict[str, Any] = {
        "filename": os.path.basename(file_path),
        "valid": False,
        "width": None,
        "height": None,
        "band_count": None,
        "crs": None,
        "crs_epsg": None,
        "transform": None,
        "bounds": None,
        "data_type": None,
        "nodata": None,
        "sensor": None,
        "polarizations": None,
        "is_sar": False,
        "error": None,
    }

    if not RASTERIO_AVAILABLE:
        result["error"] = (
            "rasterio is not installed. Run: pip install rasterio"
        )
        return result

    if not os.path.isfile(file_path):
        result["error"] = f"File not found: {file_path}"
        return result

    try:
        with rasterio.open(file_path) as ds:
            result["width"] = ds.width
            result["height"] = ds.height
            result["band_count"] = ds.count
            result["data_type"] = str(ds.dtypes[0])
            result["nodata"] = float(ds.nodata) if ds.nodata is not None else None

            # CRS & Transform validation (supports standard affine transform or Sentinel-1 GCPs)
            if ds.crs is None:
                if ds.gcps and ds.gcps[0]:
                    gcp_crs = ds.gcps[1] or CRS.from_epsg(4326)
                    result["crs"] = str(gcp_crs)
                    try:
                        result["crs_epsg"] = gcp_crs.to_epsg()
                    except Exception:
                        result["crs_epsg"] = 4326
                    t = from_gcps(ds.gcps[0])
                    result["transform"] = [t.a, t.b, t.c, t.d, t.e, t.f]
                    b = rasterio.transform.array_bounds(ds.height, ds.width, t)
                    result["bounds"] = {
                        "left": b[0],
                        "bottom": b[1],
                        "right": b[2],
                        "top": b[3],
                    }
                else:
                    result["error"] = "File has no CRS (coordinate reference system) defined."
                    return result
            else:
                result["crs"] = str(ds.crs)
                try:
                    result["crs_epsg"] = ds.crs.to_epsg()
                except Exception:
                    result["crs_epsg"] = None

                # Transform validation — reject identity / null transforms unless GCPs present
                t = ds.transform
                coeffs = [t.a, t.b, t.c, t.d, t.e, t.f]
                if t.a == 1.0 and t.e == 1.0 and t.c == 0.0 and t.f == 0.0:
                    if ds.gcps and ds.gcps[0]:
                        t_gcp = from_gcps(ds.gcps[0])
                        result["transform"] = [t_gcp.a, t_gcp.b, t_gcp.c, t_gcp.d, t_gcp.e, t_gcp.f]
                        b = rasterio.transform.array_bounds(ds.height, ds.width, t_gcp)
                        result["bounds"] = {
                            "left": b[0],
                            "bottom": b[1],
                            "right": b[2],
                            "top": b[3],
                        }
                    else:
                        result["error"] = (
                            "File has a default/identity affine transform. "
                            "The image is missing geospatial georeferencing."
                        )
                        return result
                else:
                    result["transform"] = coeffs

                    # Bounding box
                    b = ds.bounds
                    result["bounds"] = {
                        "left": b.left,
                        "bottom": b.bottom,
                        "right": b.right,
                        "top": b.top,
                    }

            if ds.count < 1:
                result["error"] = "File has no raster bands."
                return result

            is_sar, sensor, pols, is_db = inspect_sar_properties(ds)
            result["sensor"] = sensor
            result["polarizations"] = pols if pols else None
            result["is_sar"] = is_sar

            result["valid"] = True

    except rasterio.errors.RasterioIOError as exc:
        result["error"] = f"Cannot read file: {exc}"
    except Exception as exc:
        result["error"] = f"Unexpected error reading file: {exc}"

    return result


def validate_image_pair(pre_path: str, post_path: str) -> Dict[str, Any]:
    """
    Validate a pre/post GeoTIFF pair for spatial compatibility.

    Returns dict with: pre_flood, post_flood, compatible, compatibility_notes.
    """
    pre_result = validate_geotiff(pre_path)
    post_result = validate_geotiff(post_path)

    notes = []
    compatible = pre_result["valid"] and post_result["valid"]

    if compatible:
        # Sentinel-1 SAR compatibility
        if pre_result.get("is_sar") and post_result.get("is_sar"):
            pre_pols = set(pre_result.get("polarizations") or [])
            post_pols = set(post_result.get("polarizations") or [])
            common_pols = pre_pols.intersection(post_pols)
            active_pols = sorted(common_pols or (pre_pols | post_pols))
            pol_str = f" (Polarisations: {', '.join(active_pols)})" if active_pols else ""
            notes.append(
                f"Sentinel-1 SAR image pair validated{pol_str}. "
                "Calibrated radar backscatter drop detection will be used for flood inundation mapping."
            )
        elif pre_result.get("is_sar") or post_result.get("is_sar"):
            notes.append(
                "Mixed sensor pair detected (one image is SAR, one is optical). "
                "Differencing will proceed with caution."
            )

        # CRS compatibility check
        if pre_result["crs"] != post_result["crs"]:
            notes.append(
                f"CRS mismatch — pre: {pre_result['crs']}, post: {post_result['crs']}. "
                "Images will be reprojected during analysis."
            )

        # Bounding box overlap check
        if pre_result["bounds"] and post_result["bounds"]:
            pre_b = pre_result["bounds"]
            post_b = post_result["bounds"]
            overlaps = (
                pre_b["left"] < post_b["right"]
                and pre_b["right"] > post_b["left"]
                and pre_b["bottom"] < post_b["top"]
                and pre_b["top"] > post_b["bottom"]
            )
            if not overlaps:
                notes.append(
                    "WARNING: Pre-flood and post-flood images do not appear to overlap spatially. "
                    "Flood detection results may be unreliable."
                )
                compatible = False
            else:
                notes.append("Spatial extents overlap — images are geographically compatible.")

        # Resolution/dimension compatibility
        if (
            pre_result["width"] and post_result["width"]
            and pre_result["height"] and post_result["height"]
        ):
            width_ratio = max(pre_result["width"], post_result["width"]) / max(
                min(pre_result["width"], post_result["width"]), 1
            )
            if width_ratio > 4:
                notes.append(
                    "Image dimensions differ significantly. "
                    "The post-image will be resampled to match the pre-image during analysis."
                )

        # Band count note
        if (
            pre_result["band_count"] is not None
            and post_result["band_count"] is not None
            and pre_result["band_count"] != post_result["band_count"]
        ):
            notes.append(
                f"Band count differs — pre: {pre_result['band_count']}, "
                f"post: {post_result['band_count']}. Single-band differencing will be used."
            )

    return {
        "pre_flood": pre_result,
        "post_flood": post_result,
        "compatible": compatible,
        "compatibility_notes": notes,
    }


def save_upload_file(file_obj: Any, destination_dir: str, filename: str) -> str:
    """
    Save a file-like object or bytes to destination_dir/filename.
    Creates destination_dir if it does not exist.
    Returns the full saved path.
    """
    os.makedirs(destination_dir, exist_ok=True)
    dest_path = os.path.join(destination_dir, filename)

    if hasattr(file_obj, "read"):
        content = file_obj.read()
        if hasattr(content, "__await__"):
            raise ValueError("Use save_upload_file_async for async file objects.")
    elif isinstance(file_obj, (bytes, bytearray)):
        content = file_obj
    else:
        raise ValueError(f"Unsupported file object type: {type(file_obj)}")

    with open(dest_path, "wb") as f:
        f.write(content)

    return dest_path


async def save_upload_file_async(upload_file: Any, destination_dir: str, filename: str) -> str:
    """
    Async version for saving FastAPI UploadFile objects.
    """
    os.makedirs(destination_dir, exist_ok=True)
    dest_path = os.path.join(destination_dir, filename)
    content = await upload_file.read()
    with open(dest_path, "wb") as f:
        f.write(content)
    return dest_path
