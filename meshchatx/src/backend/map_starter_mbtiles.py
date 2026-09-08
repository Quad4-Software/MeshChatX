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
STARTER_NAME = "MeshChatX starter world graticule (z0-z4)"
STARTER_ATTRIBUTION = (
    "Generated low-zoom graticule. Replace with OSM or other MBTiles for detail."
)
STARTER_MAX_ZOOM = 4

# Package-data directory relative to this file: backend/data/map/
_DATA_DIR = Path(__file__).resolve().parent / "data" / "map"
_bundled_starter_lock = threading.Lock()


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


def _graticule_tile_png(
    z: int, x: int, y: int, width: int = 256, height: int = 256
) -> bytes:
    bg = bytes([15, 23, 42, 255])
    grid = bytes([51, 65, 85, 255])
    prime = bytes([56, 189, 248, 255])
    n = 1 << z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = _mercator_lat(y / n)
    south = _mercator_lat((y + 1) / n)

    pixels = bytearray(width * height * 4)
    for i in range(0, len(pixels), 4):
        pixels[i : i + 4] = bg

    for lon in range(-180, 181, 30):
        if lon < west or lon > east:
            continue
        col = int(round((lon - west) / (east - west) * (width - 1)))
        col = max(0, min(width - 1, col))
        color = prime if lon == 0 else grid
        for row in range(height):
            idx = (row * width + col) * 4
            pixels[idx : idx + 4] = color

    for lat in range(-90, 91, 30):
        if lat < south or lat > north:
            continue
        row = int(round((north - lat) / (north - south) * (height - 1)))
        row = max(0, min(height - 1, row))
        color = prime if lat == 0 else grid
        row_start = row * width * 4
        pixels[row_start : row_start + width * 4] = color * width

    if 0 >= west and 0 <= east and 0 >= south and 0 <= north:
        col = int(round((0 - west) / (east - west) * (width - 1)))
        row = int(round((north - 0) / (north - south) * (height - 1)))
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
            rows = []
            for z in range(0, max_zoom + 1):
                n = 1 << z
                for x in range(n):
                    for y in range(n):
                        # MBTiles uses TMS Y (flip from XYZ).
                        tms_y = (n - 1) - y
                        rows.append((z, x, tms_y, _graticule_tile_png(z, x, y)))
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
