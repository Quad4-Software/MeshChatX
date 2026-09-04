# SPDX-License-Identifier: 0BSD

"""Generate and locate the bundled low-zoom starter MBTiles basemap."""

from __future__ import annotations

import sqlite3
import struct
import zlib
from pathlib import Path


STARTER_FILENAME = "starter_world.mbtiles"
STARTER_NAME = "MeshChatX starter world (z0-z4)"
STARTER_ATTRIBUTION = (
    "Generated low-zoom placeholder. Replace with OSM or other MBTiles for detail."
)
STARTER_MAX_ZOOM = 4

# Package-data directory relative to this file: backend/data/map/
_DATA_DIR = Path(__file__).resolve().parent / "data" / "map"


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


def write_starter_mbtiles(dest: str | Path, max_zoom: int = STARTER_MAX_ZOOM) -> Path:
    """Write a raster MBTiles with solid tiles covering the world up to max_zoom."""
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()

    tile_png = solid_png_rgba(
        256, 256, (70, 130, 180, 255)
    )  # steel blue ocean placeholder

    conn = sqlite3.connect(str(dest_path))
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
                    rows.append((z, x, tms_y, tile_png))
        cur.executemany(
            "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return dest_path


def ensure_bundled_starter_file() -> Path:
    """Create the package-data starter file if missing. Returns its path."""
    path = bundled_starter_path()
    if path.is_file() and path.stat().st_size > 1024:
        return path
    return write_starter_mbtiles(path)
