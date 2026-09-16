"""
Standalone Synthetic GeoTIFF Builder for SatQuery.
Generates sample_pre_flood_sentinel.tif and sample_post_flood_sentinel.tif (and DEM).
Can generate standard valid GeoTIFFs using rasterio OR pure-Python binary TIFF encoder.
"""

import os
import struct
import numpy as np

# Bounding box coordinates (WGS84)
# Center: 72.9° E, 19.0° N (Maharashtra/Gujarat region)
MIN_LON, MAX_LON = 72.80, 73.00
MIN_LAT, MAX_LAT = 18.90, 19.10
WIDTH, HEIGHT = 200, 200


def create_geotiff_pure_python(filename: str, array_2d: np.ndarray, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """
    Write a 2D float32 numpy array as a valid uncompressed GeoTIFF (EPSG:4326).
    Complies with TIFF 6.0 and GeoTIFF 1.0 specifications.
    """
    h, w = array_2d.shape
    pixel_scale_x = (max_lon - min_lon) / w
    pixel_scale_y = (max_lat - min_lat) / h

    raw_data = array_2d.astype(np.float32).tobytes()
    raw_data_len = len(raw_data)

    # We will lay out the file:
    # 0..7: Header (II, 42, offset to IFD = 8)
    # 8..: IFD entries
    # Then extra data values (doubles, geokeys)
    # Then pixel data

    # GeoKey Directory values
    # Header: Version 1, KeyRevision 1, MinorRevision 0, NumberOfKeys 3
    # Keys:
    # 1. GTModelTypeGeoKey (1024) -> 2 (ModelTypeGeographic)
    # 2. GTRasterTypeGeoKey (1025) -> 1 (RasterPixelIsArea)
    # 3. GeographicTypeGeoKey (2048) -> 4326 (WGS 84)
    geokeys = [
        1, 1, 0, 3,
        1024, 0, 1, 2,
        1025, 0, 1, 1,
        2048, 0, 1, 4326,
    ]
    geokeys_bytes = struct.pack(f"<{len(geokeys)}H", *geokeys)

    model_pixel_scale = [pixel_scale_x, pixel_scale_y, 0.0]
    model_pixel_scale_bytes = struct.pack("<3d", *model_pixel_scale)

    model_tiepoint = [0.0, 0.0, 0.0, min_lon, max_lat, 0.0]
    model_tiepoint_bytes = struct.pack("<6d", *model_tiepoint)

    num_tags = 12
    ifd_offset = 8
    # 2 bytes count + num_tags * 12 + 4 bytes next IFD offset
    ifd_size = 2 + num_tags * 12 + 4
    extra_data_offset = ifd_offset + ifd_size

    # Position extra data blocks
    pixel_scale_offset = extra_data_offset
    tiepoint_offset = pixel_scale_offset + len(model_pixel_scale_bytes)
    geokeys_offset = tiepoint_offset + len(model_tiepoint_bytes)
    pixel_data_offset = geokeys_offset + len(geokeys_bytes)

    # Pad pixel data offset to 4-byte boundary
    if pixel_data_offset % 4 != 0:
        pixel_data_offset += (4 - (pixel_data_offset % 4))

    # Construct IFD tags in ascending numerical order (required by TIFF spec):
    # 256: ImageWidth (LONG, 1)
    # 257: ImageLength (LONG, 1)
    # 258: BitsPerSample (SHORT, 1) -> 32
    # 259: Compression (SHORT, 1) -> 1 (uncompressed)
    # 262: PhotometricInterpretation (SHORT, 1) -> 1 (BlackIsZero)
    # 273: StripOffsets (LONG, 1) -> pixel_data_offset
    # 277: SamplesPerPixel (SHORT, 1) -> 1
    # 278: RowsPerStrip (LONG, 1) -> h
    # 279: StripByteCounts (LONG, 1) -> raw_data_len
    # 339: SampleFormat (SHORT, 1) -> 3 (IEEE float)
    # 33550: ModelPixelScaleTag (DOUBLE, 3) -> pixel_scale_offset
    # 33922: ModelTiepointTag (DOUBLE, 6) -> tiepoint_offset
    # 34735: GeoKeyDirectoryTag (SHORT, 16) -> geokeys_offset

    tags = [
        (256, 4, 1, w),
        (257, 4, 1, h),
        (258, 3, 1, 32),
        (259, 3, 1, 1),
        (262, 3, 1, 1),
        (273, 4, 1, pixel_data_offset),
        (277, 3, 1, 1),
        (278, 4, 1, h),
        (279, 4, 1, raw_data_len),
        (339, 3, 1, 3),
        (33550, 12, 3, pixel_scale_offset),
        (33922, 12, 6, tiepoint_offset),
        (34735, 3, len(geokeys), geokeys_offset),
    ]
    # Sort tags by tag ID
    tags.sort(key=lambda t: t[0])

    with open(filename, "wb") as f:
        # Header
        f.write(b"II\x2a\x00\x08\x00\x00\x00")

        # IFD count
        f.write(struct.pack("<H", len(tags)))

        # Tags
        for tag_id, tag_type, count, val in tags:
            f.write(struct.pack("<HHI", tag_id, tag_type, count))
            # If value fits in 4 bytes and is not an offset
            if tag_type == 3 and count == 1:  # SHORT
                f.write(struct.pack("<HH", val, 0))
            elif tag_type == 4 and count == 1:  # LONG
                f.write(struct.pack("<I", val))
            else:  # offset
                f.write(struct.pack("<I", val))

        # Next IFD (0 = none)
        f.write(struct.pack("<I", 0))

        # Extra data
        f.write(model_pixel_scale_bytes)
        f.write(model_tiepoint_bytes)
        f.write(geokeys_bytes)

        # Pad to pixel_data_offset
        current_pos = f.tell()
        if current_pos < pixel_data_offset:
            f.write(b"\x00" * (pixel_data_offset - current_pos))

        # Pixel data
        f.write(raw_data)

    return filename


def generate_all_sample_files(base_data_dir: str):
    os.makedirs(os.path.join(base_data_dir, "input"), exist_ok=True)
    os.makedirs(os.path.join(base_data_dir, "dem"), exist_ok=True)

    # 1. Pre-flood baseline: background dry value ~30.0 with minor river line
    pre_data = np.full((HEIGHT, WIDTH), 30.0, dtype=np.float32)
    # Add subtle terrain noise
    np.random.seed(10)
    pre_data += np.random.uniform(0.0, 5.0, (HEIGHT, WIDTH)).astype(np.float32)
    # Permanent small water stream
    pre_data[98:102, :] = 15.0

    # 2. Post-flood image: substantial flood plume in central valley (rows 65:135, cols 40:150)
    post_data = np.copy(pre_data)
    # Significant flood inundation signal
    post_data[65:135, 40:150] += 160.0
    post_data[60:75, 50:110] += 120.0

    # 3. DEM Elevation: 10m in west to 75m in east
    x_coords = np.linspace(0, 1, WIDTH)
    y_coords = np.linspace(0, 1, HEIGHT)
    xx, yy = np.meshgrid(x_coords, y_coords)
    dem_data = (10.0 + 65.0 * xx + 10.0 * yy).astype(np.float32)

    pre_file = os.path.join(base_data_dir, "input", "sample_pre_flood_sentinel.tif")
    post_file = os.path.join(base_data_dir, "input", "sample_post_flood_sentinel.tif")
    dem_file = os.path.join(base_data_dir, "dem", "dem_elevation.tif")

    # Try rasterio first, fallback to pure python
    written = False
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS
        transform = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, WIDTH, HEIGHT)
        crs = CRS.from_epsg(4326)

        profile = {
            "driver": "GTiff",
            "height": HEIGHT,
            "width": WIDTH,
            "count": 1,
            "dtype": rasterio.float32,
            "crs": crs,
            "transform": transform,
            "nodata": -9999.0,
        }
        with rasterio.open(pre_file, "w", **profile) as dst:
            dst.write(pre_data, 1)
        with rasterio.open(post_file, "w", **profile) as dst:
            dst.write(post_data, 1)
        with rasterio.open(dem_file, "w", **profile) as dst:
            dst.write(dem_data, 1)
        written = True
    except Exception:
        pass

    if not written:
        create_geotiff_pure_python(pre_file, pre_data, MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)
        create_geotiff_pure_python(post_file, post_data, MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)
        create_geotiff_pure_python(dem_file, dem_data, MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)

    print(f"Created: {pre_file}")
    print(f"Created: {post_file}")
    print(f"Created: {dem_file}")
    return pre_file, post_file, dem_file


if __name__ == "__main__":
    generate_all_sample_files(r"c:\SatQuery\data")
