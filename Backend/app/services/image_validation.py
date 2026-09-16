"""
Image Validation Service.

Validates GeoTIFF files for geospatial completeness and pair-compatibility.
All rasterio imports are wrapped to provide clear error messages when the
package is not yet installed.
"""

import os
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Rasterio import guard
# ---------------------------------------------------------------------------
try:
    import rasterio
    from rasterio.crs import CRS
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False


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

            # CRS validation
            if ds.crs is None:
                result["error"] = "File has no CRS (coordinate reference system) defined."
                return result
            result["crs"] = str(ds.crs)
            try:
                result["crs_epsg"] = ds.crs.to_epsg()
            except Exception:
                result["crs_epsg"] = None

            # Transform validation — reject identity / null transforms
            t = ds.transform
            coeffs = [t.a, t.b, t.c, t.d, t.e, t.f]
            if t.a == 1.0 and t.e == 1.0 and t.c == 0.0 and t.f == 0.0:
                result["error"] = (
                    "File has a default/identity affine transform. "
                    "The image is missing geospatial georeferencing."
                )
                return result
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
