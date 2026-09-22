"""
Deterministic Flood Detection Service.

Implements change detection using:
1. NDWI (Normalized Difference Water Index) for multi-band optical imagery
2. Image differencing + Otsu thresholding for single-band or SAR imagery

All ML model imports are deliberately absent — this is a pure deterministic baseline.
A U-Net / Sen1Floods11 model can be plugged in as an alternative method later.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dependency guards
# ---------------------------------------------------------------------------
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import rasterio
    from rasterio.warp import reproject, Resampling, calculate_default_transform
    from rasterio.crs import CRS
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    from scipy import ndimage as ndi
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class FloodDetectionService:
    """
    Deterministic satellite-based flood extent detection.

    Supports:
      - NDWI differencing for multi-band optical imagery
      - Band differencing + Otsu thresholding for single-band/SAR
    """

    def detect(
        self,
        pre_path: str,
        post_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run flood detection pipeline on a pre/post image pair.

        Returns a result dict containing:
          success, method_used, flooded_pixels, total_pixels, flood_percentage,
          flood_area_km2, bounds, mask_array (numpy), mask_path, crs, notes, error
        """
        if not RASTERIO_AVAILABLE:
            return self._error_result("rasterio is not installed. Run: pip install rasterio")
        if not NUMPY_AVAILABLE:
            return self._error_result("numpy is not installed. Run: pip install numpy")

        opts = options or {}
        method = opts.get("method", "auto")
        morphology_iters = int(opts.get("morphology_iterations", 2))

        notes: List[str] = []

        try:
            with rasterio.open(pre_path) as pre_ds, rasterio.open(post_path) as post_ds:
                # Select detection method
                if method == "ndwi" or (
                    method == "auto"
                    and pre_ds.count >= 3
                    and post_ds.count >= 3
                ):
                    try:
                        mask, method_used, step_notes = self._ndwi_detection(
                            pre_ds, post_ds, opts
                        )
                        notes.extend(step_notes)
                    except Exception as exc:
                        notes.append(f"NDWI detection failed ({exc}); falling back to differencing.")
                        mask, method_used, step_notes = self._differencing_detection(
                            pre_ds, post_ds, opts
                        )
                        notes.extend(step_notes)
                else:
                    mask, method_used, step_notes = self._differencing_detection(
                        pre_ds, post_ds, opts
                    )
                    notes.extend(step_notes)

                # Morphological cleanup
                if morphology_iters > 0:
                    mask = self._morphological_cleanup(mask, morphology_iters)
                    notes.append(f"Morphological cleanup applied ({morphology_iters} iterations).")

                # Statistics
                total_pixels = int(mask.size)
                flooded_pixels = int(np.sum(mask > 0))
                flood_pct = round((flooded_pixels / max(total_pixels, 1)) * 100, 4)

                # Area estimation
                flood_area_km2 = self._compute_area_km2(mask, pre_ds.transform, pre_ds.crs)

                # Save mask raster
                from app.core.config import settings
                output_dir = settings.data_output_dir
                os.makedirs(output_dir, exist_ok=True)
                mask_filename = f"flood_mask_{os.path.basename(pre_path)}"
                mask_path = os.path.join(output_dir, mask_filename)
                self._save_mask(mask, pre_ds, mask_path)

                b = pre_ds.bounds
                return {
                    "success": True,
                    "method_used": method_used,
                    "flooded_pixels": flooded_pixels,
                    "total_pixels": total_pixels,
                    "flood_percentage": flood_pct,
                    "flood_area_km2": round(flood_area_km2, 4),
                    "bounds": {
                        "left": b.left,
                        "bottom": b.bottom,
                        "right": b.right,
                        "top": b.top,
                    },
                    "mask_array": mask,
                    "mask_path": mask_path,
                    "crs": str(pre_ds.crs),
                    "notes": notes,
                    "error": None,
                }

        except Exception as exc:
            logger.exception("Flood detection failed")
            return self._error_result(str(exc))

    # ------------------------------------------------------------------
    # NDWI Detection
    # ------------------------------------------------------------------

    def _ndwi_detection(
        self,
        pre_ds: Any,
        post_ds: Any,
        opts: Dict[str, Any],
    ) -> Tuple[Any, str, List[str]]:
        """
        NDWI-based water change detection.

        NDWI = (Green - NIR) / (Green + NIR)
        Positive NDWI values indicate water. Pixels where post-NDWI > pre-NDWI
        and post-NDWI > threshold are classified as new flood water.
        """
        notes: List[str] = []
        green_idx = int(opts.get("ndwi_green_band", 2)) - 1  # convert to 0-indexed
        nir_idx = int(opts.get("ndwi_nir_band", 4)) - 1

        # Clamp to available bands
        green_idx = min(green_idx, pre_ds.count - 1)
        nir_idx = min(nir_idx, pre_ds.count - 1)

        pre_green = pre_ds.read(green_idx + 1).astype(np.float32)
        pre_nir = pre_ds.read(nir_idx + 1).astype(np.float32)
        post_green = post_ds.read(green_idx + 1).astype(np.float32)
        post_nir = post_ds.read(nir_idx + 1).astype(np.float32)

        # Reproject post to match pre if needed
        if (
            pre_ds.crs != post_ds.crs
            or pre_ds.width != post_ds.width
            or pre_ds.height != post_ds.height
        ):
            post_green, post_nir = self._reproject_bands_to_match(
                pre_ds, post_ds, [green_idx, nir_idx]
            )
            notes.append("Post-image reprojected/resampled to match pre-image for NDWI.")

        # Compute NDWI for both images
        pre_ndwi = (pre_green - pre_nir) / (pre_green + pre_nir + 1e-10)
        post_ndwi = (post_green - post_nir) / (post_green + post_nir + 1e-10)

        threshold = opts.get("threshold")
        if threshold is None:
            threshold = 0.0  # Standard water/non-water NDWI boundary

        # Flood = pixels that are water in post but not (or less) in pre
        post_water = (post_ndwi > threshold).astype(np.uint8)
        pre_water = (pre_ndwi > threshold).astype(np.uint8)
        flood_mask = np.where(post_water > pre_water, 1, 0).astype(np.uint8)

        notes.append(
            f"NDWI detection: green_band={green_idx+1}, nir_band={nir_idx+1}, "
            f"water_threshold={threshold}"
        )
        return flood_mask, "ndwi", notes

    # ------------------------------------------------------------------
    # Image Differencing + Otsu Detection
    # ------------------------------------------------------------------

    def _differencing_detection(
        self,
        pre_ds: Any,
        post_ds: Any,
        opts: Dict[str, Any],
    ) -> Tuple[Any, str, List[str]]:
        """
        Absolute image differencing with Otsu thresholding.

        Computes |post_band1 - pre_band1| and applies Otsu threshold
        to separate background from flood-change pixels.
        """
        notes: List[str] = []

        pre_band = pre_ds.read(1).astype(np.float32)

        # Reproject post band 1 to pre's grid if needed
        if (
            pre_ds.crs != post_ds.crs
            or pre_ds.width != post_ds.width
            or pre_ds.height != post_ds.height
        ):
            post_band = np.zeros_like(pre_band)
            reproject(
                source=rasterio.band(post_ds, 1),
                destination=post_band,
                src_transform=post_ds.transform,
                src_crs=post_ds.crs,
                dst_transform=pre_ds.transform,
                dst_crs=pre_ds.crs,
                resampling=Resampling.bilinear,
            )
            notes.append("Post-image reprojected to match pre-image grid for differencing.")
        else:
            post_band = post_ds.read(1).astype(np.float32)

        # Mask out nodata
        nodata_pre = pre_ds.nodata
        nodata_post = post_ds.nodata
        valid_mask = np.ones(pre_band.shape, dtype=bool)
        if nodata_pre is not None:
            valid_mask &= pre_band != nodata_pre
        if nodata_post is not None:
            valid_mask &= post_band != nodata_post

        diff = np.abs(post_band - pre_band)
        diff[~valid_mask] = 0.0

        # Determine threshold
        user_threshold = opts.get("threshold")
        if user_threshold is not None:
            threshold = float(user_threshold)
            notes.append(f"Using user-supplied threshold: {threshold:.4f}")
        else:
            threshold = self._otsu_threshold(diff[valid_mask])
            notes.append(f"Otsu auto-threshold computed: {threshold:.4f}")

        flood_mask = (diff > threshold).astype(np.uint8)
        return flood_mask, "differencing+otsu", notes

    # ------------------------------------------------------------------
    # Otsu Threshold (pure numpy)
    # ------------------------------------------------------------------

    def _otsu_threshold(self, data: Any) -> float:
        """
        Pure numpy Otsu threshold maximizing inter-class variance.
        Handles flat or nearly uniform arrays gracefully.
        """
        if data.size == 0:
            return 0.0

        data_min, data_max = data.min(), data.max()
        if data_max - data_min < 1e-10:
            return float(data_min)

        # Normalize to [0, 255] integer bins
        normalized = ((data - data_min) / (data_max - data_min) * 255).astype(np.int32)
        hist, bin_edges = np.histogram(normalized, bins=256, range=(0, 255))
        total = hist.sum()
        if total == 0:
            return float((data_min + data_max) / 2)

        hist = hist.astype(np.float64)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

        # Cumulative sums for inter-class variance maximization
        weight_bg = np.cumsum(hist)
        weight_fg = total - weight_bg

        sum_total = np.sum(bin_centers * hist)
        sum_bg = np.cumsum(bin_centers * hist)
        mean_bg = np.where(weight_bg > 0, sum_bg / weight_bg, 0.0)
        mean_fg = np.where(weight_fg > 0, (sum_total - sum_bg) / weight_fg, 0.0)

        inter_class_var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        optimal_bin = int(np.argmax(inter_class_var))

        # Scale threshold back to original data range
        threshold_normalized = bin_centers[optimal_bin]
        threshold = data_min + (threshold_normalized / 255.0) * (data_max - data_min)
        return float(threshold)

    # ------------------------------------------------------------------
    # Morphological Cleanup
    # ------------------------------------------------------------------

    def _morphological_cleanup(self, mask: Any, iterations: int = 2) -> Any:
        """
        Remove salt-and-pepper noise from the binary flood mask.

        Uses binary opening (removes small objects) then closing (fills small holes).
        Falls back to simple connected-component filtering if scipy is unavailable.
        """
        if not SCIPY_AVAILABLE:
            # Minimal fallback: remove isolated single pixels via label analysis
            return mask

        struct = ndi.generate_binary_structure(2, 2)  # 8-connectivity
        cleaned = ndi.binary_opening(mask, structure=struct, iterations=iterations)
        cleaned = ndi.binary_closing(cleaned, structure=struct, iterations=iterations)

        # Remove very small isolated components (< 50 pixels)
        labeled, num_features = ndi.label(cleaned)
        if num_features > 0:
            component_sizes = ndi.sum(cleaned, labeled, range(1, num_features + 1))
            small_mask = np.array(component_sizes) < 50
            for i, is_small in enumerate(small_mask):
                if is_small:
                    cleaned[labeled == (i + 1)] = 0

        return cleaned.astype(np.uint8)

    # ------------------------------------------------------------------
    # Area Calculation
    # ------------------------------------------------------------------

    def _compute_area_km2(self, mask: Any, transform: Any, crs: Any) -> float:
        """
        Estimate the total flooded area in square kilometres.

        Uses pixel dimensions from the affine transform. For geographic CRS
        (degrees), applies a cosine-latitude correction.
        """
        flooded = int(np.sum(mask > 0))
        if flooded == 0:
            return 0.0

        px_width = abs(transform.a)
        px_height = abs(transform.e)

        try:
            is_geographic = crs.is_geographic
        except Exception:
            is_geographic = True  # Default to geographic (degrees) assumption

        if is_geographic:
            # Approximate conversion: 1 degree ≈ 111.32 km at equator
            # Use pixel centre latitude for cos correction
            centre_lat_deg = transform.f + (mask.shape[0] / 2) * transform.e
            import math
            cos_lat = math.cos(math.radians(centre_lat_deg))
            pixel_area_km2 = (px_width * 111.32 * cos_lat) * (px_height * 111.32)
        else:
            # Projected CRS — pixel size is already in metres
            pixel_area_km2 = (px_width / 1000.0) * (px_height / 1000.0)

        return abs(flooded * pixel_area_km2)

    # ------------------------------------------------------------------
    # Save Mask Raster
    # ------------------------------------------------------------------

    def _save_mask(self, mask: Any, reference_ds: Any, output_path: str) -> str:
        """Write a binary uint8 GeoTIFF flood mask, copying CRS and transform."""
        profile = reference_ds.profile.copy()
        profile.update(
            dtype=rasterio.uint8,
            count=1,
            compress="lzw",
            nodata=255,
        )
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(mask.astype(np.uint8), 1)
        return output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reproject_bands_to_match(
        self, pre_ds: Any, post_ds: Any, band_indices: List[int]
    ) -> Tuple:
        """Reproject specified bands from post_ds to match pre_ds grid."""
        arrays = []
        for band_idx in band_indices:
            dest = np.zeros((pre_ds.height, pre_ds.width), dtype=np.float32)
            reproject(
                source=rasterio.band(post_ds, band_idx + 1),
                destination=dest,
                src_transform=post_ds.transform,
                src_crs=post_ds.crs,
                dst_transform=pre_ds.transform,
                dst_crs=pre_ds.crs,
                resampling=Resampling.bilinear,
            )
            arrays.append(dest)
        return tuple(arrays)

    @staticmethod
    def _error_result(message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "method_used": "none",
            "flooded_pixels": 0,
            "total_pixels": 0,
            "flood_percentage": 0.0,
            "flood_area_km2": 0.0,
            "bounds": None,
            "mask_array": None,
            "mask_path": None,
            "crs": None,
            "notes": [],
            "error": message,
        }
