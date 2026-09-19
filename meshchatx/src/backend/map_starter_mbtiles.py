# SPDX-License-Identifier: 0BSD

"""Generate and locate the bundled low-zoom starter MBTiles basemap."""

from __future__ import annotations

import math
import os
import sqlite3
import struct
import threading
import zlib
from pathlib import Path

STARTER_FILENAME = "starter_world.mbtiles"
STARTER_NAME = "MeshChatX starter world (Natural Earth 110m land, z0-z4)"
STARTER_ATTRIBUTION = (
    "Land polygons: Natural Earth (public domain). "
    "Generated low-zoom basemap. Replace with OSM or other MBTiles for detail."
)
STARTER_MAX_ZOOM = 4

# Package-data directory relative to this file: backend/data/map/
_DATA_DIR = Path(__file__).resolve().parent / "data" / "map"
_LAND_GEOJSON_PATH = _DATA_DIR / "ne_110m_land.geojson"
_bundled_starter_lock = threading.Lock()
_land_rings_cache = None
_land_rings_loaded = False

_MAX_LAT = 85.05112878

_BG = bytes([15, 23, 42, 255])
_LAND = bytes([30, 41, 59, 255])
_COAST = bytes([100, 116, 139, 255])
_GRID = bytes([51, 65, 85, 255])
_PRIME = bytes([56, 189, 248, 255])


def bundled_starter_path() -> Path:
    """Return the path to the packaged starter MBTiles (may not exist yet)."""
    return _DATA_DIR / STARTER_FILENAME


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def solid_png_rgba(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    """Build a minimal RGBA PNG without third-party deps."""
    r, g, b, a = rgba
    row = bytes([0]) + bytes([r, g, b, a]) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def _png_rgba_raster(pixels: bytearray, width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = bytearray()
    for row in range(height):
        raw.append(0)
        row_start = row * width * 4
        raw.extend(pixels[row_start : row_start + width * 4])
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def _mercator_lat(y_norm: float) -> float:
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y_norm))))


def _mercator_project(lon: float, lat: float, world_px: int) -> tuple[float, float]:
    lat = max(-_MAX_LAT, min(_MAX_LAT, lat))
    px = (lon + 180.0) / 360.0 * world_px
    siny = math.sin(math.radians(lat))
    py = (0.5 - math.log((1.0 + siny) / (1.0 - siny)) / (4.0 * math.pi)) * world_px
    return px, py


def _load_land_rings() -> list:
    """Load land polygon rings from the bundled Natural Earth GeoJSON.

    Source: Natural Earth ne_110m_land (public domain).
    Returns a list of rings; each ring is a list of [lon, lat] pairs.
    """
    global _land_rings_cache, _land_rings_loaded
    if _land_rings_loaded:
        return _land_rings_cache or []
    rings = []
    try:
        import json

        data = json.loads(_LAND_GEOJSON_PATH.read_text(encoding="utf-8"))
        for feat in data.get("features", []):
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates") or []
            gtype = geom.get("type")
            if gtype == "Polygon":
                coords = [coords]
            elif gtype != "MultiPolygon":
                continue
            for poly in coords:
                rings.extend(ring for ring in poly if len(ring) >= 3)
    except Exception:
        # Do not cache the failure: a later call may find the file in place.
        return []
    _land_rings_cache = rings
    _land_rings_loaded = True
    return rings


def _project_edges(rings: list, world_px: int) -> list:
    """Project all ring segments into global Web Mercator pixel space.

    Returns a list of (x1, y1, x2, y2) edges. Segments spanning more than half
    the world are antimeridian wraps and are skipped.
    """
    edges = []
    for ring in rings:
        pts = [_mercator_project(lon, lat, world_px) for lon, lat in ring]
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if abs(x2 - x1) > world_px / 2:
                continue
            edges.append((x1, y1, x2, y2))
    return edges


def _row_buckets(edges: list, world_px: int) -> list:
    """Bucket edges by the global pixel rows they vertically span."""
    buckets = [[] for _ in range(world_px)]
    for edge in edges:
        _, y1, _, y2 = edge
        lo = max(0, math.floor(min(y1, y2)))
        hi = min(world_px - 1, math.floor(max(y1, y2)))
        for r in range(lo, hi + 1):
            buckets[r].append(edge)
    return buckets


def _draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: bytes,
) -> None:
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    while True:
        if 0 <= x1 < width and 0 <= y1 < height:
            idx = (y1 * width + x1) * 4
            pixels[idx : idx + 4] = color
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x1 += sx
        if e2 <= dx:
            err += dx
            y1 += sy


def _basemap_tile_png(
    z: int,
    x: int,
    y: int,
    edges: list,
    row_buckets: list,
    width: int = 256,
    height: int = 256,
) -> bytes:
    bg = _BG
    grid = _GRID
    prime = _PRIME
    n = 1 << z
    px0 = x * width
    py0 = y * height
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = _mercator_lat(y / n)
    south = _mercator_lat((y + 1) / n)

    pixels = bytearray(bg * (width * height))

    # Land fill: even-odd scanline over polygon edges in global pixel space.
    for row in range(height):
        yg = py0 + row + 0.5
        xs = []
        for x1, y1, x2, y2 in row_buckets[py0 + row]:
            if (y1 <= yg < y2) or (y2 <= yg < y1):
                xs.append(x1 + (yg - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            lo = max(0, math.ceil(xs[i] - px0 - 0.5))
            hi = min(width, math.ceil(xs[i + 1] - px0 - 0.5))
            if hi > lo:
                start = (row * width + lo) * 4
                pixels[start : start + (hi - lo) * 4] = _LAND * (hi - lo)

    # Graticule lines at 30 degree intervals.
    for lon in range(-180, 181, 30):
        if lon < west or lon > east:
            continue
        col = round((lon - west) / (east - west) * (width - 1))
        col = max(0, min(width - 1, col))
        color = prime if lon == 0 else grid
        for row in range(height):
            idx = (row * width + col) * 4
            pixels[idx : idx + 4] = color

    for lat in range(-90, 91, 30):
        if lat < south or lat > north:
            continue
        row = round((north - lat) / (north - south) * (height - 1))
        row = max(0, min(height - 1, row))
        color = prime if lat == 0 else grid
        row_start = row * width * 4
        pixels[row_start : row_start + width * 4] = color * width

    # Coastline stroke: rasterize edges intersecting this tile.
    tile_edges = set()
    for r in range(py0, py0 + height):
        tile_edges.update(row_buckets[r])
    for x1, y1, x2, y2 in tile_edges:
        if max(x1, x2) < px0 or min(x1, x2) > px0 + width:
            continue
        _draw_line(
            pixels,
            width,
            height,
            round(x1 - px0),
            round(y1 - py0),
            round(x2 - px0),
            round(y2 - py0),
            _COAST,
        )

    if 0 >= west and 0 <= east and 0 >= south and 0 <= north:
        col = round((0 - west) / (east - west) * (width - 1))
        row = round((north - 0) / (north - south) * (height - 1))
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        for dc in range(-2, 3):
            for dr in range(-2, 3):
                cc = col + dc
                rr = row + dr
                if 0 <= cc < width and 0 <= rr < height:
                    idx = (rr * width + cc) * 4
                    pixels[idx : idx + 4] = prime

    return _png_rgba_raster(pixels, width, height)


def write_starter_mbtiles(dest: str | Path, max_zoom: int = STARTER_MAX_ZOOM) -> Path:
    """Write a raster MBTiles with solid tiles covering the world up to max_zoom.

    Writes to a sibling temp file then os.replace so concurrent readers never see
    a half-written SQLite file.
    """
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = dest_path.with_name(
        f".{dest_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        conn = sqlite3.connect(str(tmp_path))
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA journal_mode = MEMORY")
        try:
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE metadata (name TEXT, value TEXT)",
            )
            meta = {
                "name": STARTER_NAME,
                "format": "png",
                "type": "baselayer",
                "version": "1.0.0",
                "description": STARTER_ATTRIBUTION,
                "attribution": STARTER_ATTRIBUTION,
                "minzoom": "0",
                "maxzoom": str(max_zoom),
                "bounds": "-180.0,-85.05112878,180.0,85.05112878",
                "center": "0.0,0.0,1",
            }
            cur.executemany(
                "INSERT INTO metadata (name, value) VALUES (?, ?)",
                list(meta.items()),
            )
            cur.execute(
                "CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB)",
            )
            cur.execute(
                "CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)",
            )
            rings = _load_land_rings()
            rows = []
            for z in range(0, max_zoom + 1):
                n = 1 << z
                world_px = 256 * n
                edges = _project_edges(rings, world_px)
                buckets = _row_buckets(edges, world_px)
                for x in range(n):
                    for y in range(n):
                        # MBTiles uses TMS Y (flip from XYZ).
                        tms_y = (n - 1) - y
                        rows.append(
                            (
                                z,
                                x,
                                tms_y,
                                _basemap_tile_png(z, x, y, edges, buckets),
                            )
                        )
            cur.executemany(
                "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        os.replace(str(tmp_path), str(dest_path))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
    return dest_path


def ensure_bundled_starter_file() -> Path:
    """Create the package-data starter file if missing. Returns its path."""
    path = bundled_starter_path()
    if path.is_file() and path.stat().st_size > 1024:
        return path
    with _bundled_starter_lock:
        if path.is_file() and path.stat().st_size > 1024:
            return path
        return write_starter_mbtiles(path)
