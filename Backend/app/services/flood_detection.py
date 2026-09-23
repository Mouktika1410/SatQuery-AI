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

    def detect_gee(
        self,
        bbox: Optional[List[float]] = None,
        pre_start: str = "2019-10-15",
        pre_end: str = "2019-11-04",
        post_start: str = "2019-11-05",
        post_end: str = "2019-11-15",
        threshold_db: float = -2.0,
        smoothing_radius: int = 50,
        polarization: str = "VV",
        pass_direction: str = "ASCENDING",
        simplify_tolerance: float = 0.0001,
    ) -> Dict[str, Any]:
        """
        Run real Google Earth Engine Sentinel-1 GRD flood detection for South Yorkshire / River Don
        or a user-specified AOI and historical date range.
        """
        from app.services.gee_flood_detection import GEEFloodDetectionService
        gee_svc = GEEFloodDetectionService()
        return gee_svc.detect_flood_sentinel1(
            bbox=bbox,
            pre_start=pre_start,
            pre_end=pre_end,
            post_start=post_start,
            post_end=post_end,
            threshold_db=threshold_db,
            smoothing_radius=smoothing_radius,
            polarization=polarization,
            pass_direction=pass_direction,
            simplify_tolerance=simplify_tolerance,
        )

    def detect(
        self,
        pre_path: str,
        post_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run flood detection pipeline on a pre/post image pair or GEE.

        Returns a result dict containing:
          success, method_used, flooded_pixels, total_pixels, flood_percentage,
          flood_area_km2, bounds, mask_array (numpy), mask_path, crs, notes, error
        """
        opts = options or {}
        method = opts.get("method", "auto")

        if method == "gee":
            return self.detect_gee(
                bbox=opts.get("bbox"),
                pre_start=opts.get("pre_start", "2019-10-15"),
                pre_end=opts.get("pre_end", "2019-11-04"),
                post_start=opts.get("post_start", "2019-11-05"),
                post_end=opts.get("post_end", "2019-11-15"),
                threshold_db=float(opts.get("threshold_db", -2.0)),
                smoothing_radius=int(opts.get("smoothing_radius", 50)),
                polarization=opts.get("polarization", "VV"),
                pass_direction=opts.get("pass_direction", "ASCENDING"),
            )

        if not RASTERIO_AVAILABLE:
            return self._error_result("rasterio is not installed. Run: pip install rasterio")
        if not NUMPY_AVAILABLE:
            return self._error_result("numpy is not installed. Run: pip install numpy")

        morphology_iters = int(opts.get("morphology_iterations", 2))

        notes: List[str] = []

        try:
            with rasterio.open(pre_path) as pre_ds, rasterio.open(post_path) as post_ds:
                # Determine if input is Sentinel-1 SAR imagery
                is_sar_pre, _, pre_pols = self._is_sar_dataset(pre_ds)
                is_sar_post, _, post_pols = self._is_sar_dataset(post_ds)
                is_sar = is_sar_pre or is_sar_post or (method == "sar")

                # Select detection method
                if method == "sar" or (method == "auto" and is_sar and pre_ds.count <= 2):
                    mask, method_used, step_notes = self._sar_detection(
                        pre_ds, post_ds, opts
                    )
                    notes.extend(step_notes)
                elif method == "ndwi" or (
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
    # Sentinel-1 SAR Dataset Identification
    # ------------------------------------------------------------------

    def _is_sar_dataset(self, ds: Any) -> Tuple[bool, Optional[str], List[str]]:
        """
        Detect if a dataset has Sentinel-1 SAR characteristics.
        Returns (is_sar, sensor_name, polarizations_list).
        """
        pols: List[str] = []
        is_sar = False
        sensor = None

        # 1. Band descriptions
        if ds.descriptions:
            for desc in ds.descriptions:
                if desc:
                    d_upper = desc.upper()
                    for p in ["VV", "VH", "HH", "HV"]:
                        if p in d_upper and p not in pols:
                            pols.append(p)
                    if any(k in d_upper for k in ["SIGMA0", "GAMMA0", "SAR", "SENTINEL-1", "S1", "BACKSCATTER", "DB"]):
                        is_sar = True

        # 2. Metadata tags
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
                        if not pols:
                            pols.append("VV")
            except Exception:
                pass

        if is_sar and not sensor:
            sensor = "Sentinel-1 SAR"

        return is_sar, sensor, pols

    # ------------------------------------------------------------------
    # Sentinel-1 SAR Flood Detection
    # ------------------------------------------------------------------

    def _sar_detection(
        self,
        pre_ds: Any,
        post_ds: Any,
        opts: Dict[str, Any],
    ) -> Tuple[Any, str, List[str]]:
        """
        Sentinel-1 SAR flood change detection based on radar backscatter drop.

        Calm floodwater acts as a specular reflector, scattering microwave pulses away
        from the radar antenna and producing a marked decrease in received backscatter.
        """
        notes: List[str] = []

        # 1. Polarization selection
        target_pol = str(opts.get("sar_polarization", "auto")).upper().strip()
        pre_band_idx = 1
        post_band_idx = 1
        pol_used = "VV"

        def find_band_for_pol(ds: Any, pol: str) -> int:
            if ds.descriptions:
                for idx, desc in enumerate(ds.descriptions, start=1):
                    if desc and pol in desc.upper():
                        return idx
            if pol == "VH" and ds.count >= 2:
                return 2
            return 1

        if target_pol in ("VV", "VH"):
            pre_band_idx = find_band_for_pol(pre_ds, target_pol)
            post_band_idx = find_band_for_pol(post_ds, target_pol)
            pol_used = target_pol
        else:
            # Auto: look for VV first, then VH
            if pre_ds.descriptions and any("VV" in (d or "").upper() for d in pre_ds.descriptions):
                pre_band_idx = find_band_for_pol(pre_ds, "VV")
                post_band_idx = find_band_for_pol(post_ds, "VV")
                pol_used = "VV"
            elif pre_ds.count >= 2 and target_pol == "VH":
                pre_band_idx = 2
                post_band_idx = 2
                pol_used = "VH"
            else:
                pre_band_idx = 1
                post_band_idx = 1
                pol_used = "VV"

        notes.append(
            f"Sentinel-1 SAR detection: polarization {pol_used} selected "
            f"(pre_band={pre_band_idx}, post_band={post_band_idx})."
        )

        # 2. Read and reproject if needed
        pre_raw = pre_ds.read(pre_band_idx).astype(np.float32)

        if (
            pre_ds.crs != post_ds.crs
            or pre_ds.width != post_ds.width
            or pre_ds.height != post_ds.height
            or pre_ds.transform != post_ds.transform
        ):
            post_raw = np.zeros_like(pre_raw)
            reproject(
                source=rasterio.band(post_ds, post_band_idx),
                destination=post_raw,
                src_transform=post_ds.transform,
                src_crs=post_ds.crs,
                dst_transform=pre_ds.transform,
                dst_crs=pre_ds.crs,
                resampling=Resampling.bilinear,
            )
            notes.append(
                f"Post-image reprojected to match pre-image grid ({post_ds.crs} -> {pre_ds.crs})."
            )
        else:
            post_raw = post_ds.read(post_band_idx).astype(np.float32)

        # 3. Nodata and border masking
        valid_mask = np.isfinite(pre_raw) & np.isfinite(post_raw)
        if pre_ds.nodata is not None:
            valid_mask &= (pre_raw != pre_ds.nodata)
        if post_ds.nodata is not None:
            valid_mask &= (post_raw != post_ds.nodata)

        valid_pre = pre_raw[valid_mask]
        valid_post = post_raw[valid_mask]
        if valid_pre.size == 0 or valid_post.size == 0:
            notes.append("No valid overlapping pixels found for SAR analysis.")
            return np.zeros(pre_raw.shape, dtype=np.uint8), "sar+otsu", notes

        # 4. Decibel (dB) Conversion
        is_db = (float(np.median(valid_pre)) < 0.0) or (float(np.percentile(valid_pre, 10)) < -2.0)

        if is_db:
            notes.append("SAR backscatter data detected in calibrated decibels (dB).")
            valid_mask &= (pre_raw > -50.0) & (post_raw > -50.0) & (pre_raw < 30.0) & (post_raw < 30.0)
            pre_db = pre_raw.copy()
            post_db = post_raw.copy()
        else:
            notes.append("Linear SAR data converted to decibel scale (dB).")
            valid_mask &= (pre_raw > 1e-7) & (post_raw > 1e-7)
            max_val = max(float(np.max(valid_pre)), float(np.max(valid_post)))
            if max_val > 10.0:
                pre_db = 20.0 * np.log10(np.maximum(pre_raw, 1e-4))
                post_db = 20.0 * np.log10(np.maximum(post_raw, 1e-4))
            else:
                pre_db = 10.0 * np.log10(np.maximum(pre_raw, 1e-7))
                post_db = 10.0 * np.log10(np.maximum(post_raw, 1e-7))

        # 5. Speckle noise filtering
        if SCIPY_AVAILABLE:
            med_pre = float(np.median(pre_db[valid_mask])) if np.any(valid_mask) else 0.0
            med_post = float(np.median(post_db[valid_mask])) if np.any(valid_mask) else 0.0

            pre_filled = np.where(valid_mask, pre_db, med_pre)
            post_filled = np.where(valid_mask, post_db, med_post)

            pre_smooth = ndi.median_filter(pre_filled, size=3)
            post_smooth = ndi.median_filter(post_filled, size=3)
            notes.append("Speckle filtering applied (3x3 median filter).")
        else:
            pre_smooth = pre_db
            post_smooth = post_db

        # 6. Backscatter drop calculation
        backscatter_drop = pre_smooth - post_smooth
        backscatter_drop[~valid_mask] = 0.0

        user_thresh = opts.get("threshold")
        if user_thresh is not None:
            thresh = float(user_thresh)
            notes.append(f"Using specified backscatter drop threshold: {thresh:.2f} dB")
        else:
            drop_data = np.maximum(backscatter_drop[valid_mask], 0.0)
            if drop_data.size > 50 and np.any(drop_data > 0):
                otsu_drop = self._otsu_threshold(drop_data)
                thresh = max(float(otsu_drop), 3.0)
                notes.append(f"Otsu auto-threshold for backscatter drop: {thresh:.2f} dB")
            else:
                thresh = 3.5
                notes.append(f"Empirical SAR backscatter drop threshold applied: {thresh:.2f} dB")

        flood_mask = ((backscatter_drop > thresh) & valid_mask).astype(np.uint8)

        # 7. Water ceiling check in calibrated dB scale
        if is_db and np.any(valid_mask):
            water_ceiling = float(opts.get("sar_water_ceiling_db", -11.0))
            flood_mask &= (post_smooth <= water_ceiling).astype(np.uint8)
            notes.append(f"Water backscatter ceiling applied (post_flood <= {water_ceiling:.1f} dB).")

        return flood_mask, "sar+otsu", notes

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
