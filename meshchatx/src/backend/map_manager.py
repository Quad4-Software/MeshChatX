# SPDX-License-Identifier: 0BSD

import asyncio
import base64
import math
import os
import sqlite3
import threading
import time

import aiohttp
import RNS

# 1x1 transparent PNG to return when a tile is not found in offline mode
TRANSPARENT_TILE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
)

# Guardrail for MBTiles exports (world + high zoom can explode).
MAX_EXPORT_TILES = 200_000
MAX_EXPORT_RECORDS = 8
TERMINAL_EXPORT_STATUSES = frozenset({"completed", "failed"})


def is_path_within_dir(path, directory):
    """Return True when path resolves to a location inside directory."""
    from meshchatx.src.path_utils import is_path_within_dir as _is_path_within_dir

    return _is_path_within_dir(path, directory)


def is_mbtiles_filename(filename):
    return os.path.basename(filename or "").lower().endswith(".mbtiles")


class MapManager:
    def __init__(self, config_manager, storage_dir):
        self.config = config_manager
        self.storage_dir = storage_dir
        self._local = threading.local()
        self._metadata_cache = None
        self._export_progress = {}
        self._export_cancelled = set()
        self._starter_lock = threading.Lock()

    def get_connection(self, path):
        if not hasattr(self._local, "connections"):
            self._local.connections = {}

        if path not in self._local.connections:
            if not os.path.exists(path):
                return None
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.execute("PRAGMA temp_store = MEMORY")
            conn.row_factory = sqlite3.Row
            self._local.connections[path] = conn

        return self._local.connections[path]

    def get_offline_path(self):
        path = self.config.map_offline_path.get()
        if path and is_path_within_dir(path, self.storage_dir) and os.path.exists(path):
            return path

        default_path = os.path.join(self.storage_dir, "offline_map.mbtiles")
        if os.path.exists(default_path):
            return default_path

        return None

    def get_mbtiles_dir(self):
        dir_path = self.config.map_mbtiles_dir.get()
        if (
            dir_path
            and os.path.isdir(dir_path)
            and is_path_within_dir(dir_path, self.storage_dir)
        ):
            return dir_path
        return self.storage_dir

    def ensure_starter_mbtiles(self, force_restore=False):
        """Seed a low-zoom starter basemap when the user has no offline map yet.

        Returns the active offline path when seeding succeeds or an existing map
        is already configured, else None.
        """
        from meshchatx.src.backend.map_starter_mbtiles import (
            STARTER_FILENAME,
            ensure_bundled_starter_file,
        )

        with self._starter_lock:
            existing = self.get_offline_path()
            if existing and os.path.exists(existing) and not force_restore:
                return existing

            try:
                src = ensure_bundled_starter_file()
            except Exception as e:
                RNS.log(
                    f"MapManager: failed to prepare starter MBTiles: {e}",
                    RNS.LOG_WARNING,
                )
                return existing if existing and os.path.exists(existing) else None

            if not src.is_file():
                return None

            mbtiles_dir = self.get_mbtiles_dir()
            os.makedirs(mbtiles_dir, exist_ok=True)
            dest = os.path.join(mbtiles_dir, STARTER_FILENAME)
            if force_restore or not os.path.exists(dest):
                import shutil
                import tempfile

                # Copy to a temp sibling then replace so concurrent tile readers
                # never open a truncated MBTiles file.
                fd, tmp_name = tempfile.mkstemp(
                    prefix=f".{STARTER_FILENAME}.",
                    suffix=".tmp",
                    dir=mbtiles_dir,
                )
                os.close(fd)
                try:
                    shutil.copy2(str(src), tmp_name)
                    os.replace(tmp_name, dest)
                finally:
                    if os.path.exists(tmp_name):
                        try:
                            os.unlink(tmp_name)
                        except OSError:
                            pass

            self.config.map_offline_path.set(dest)
            if self.config.map_offline_enabled.get() is False and force_restore:
                self.config.map_offline_enabled.set(True)
            self._metadata_cache = None
            # Drop cached connections so the new file is opened fresh.
            if hasattr(self._local, "connections"):
                for conn in list(self._local.connections.values()):
                    try:
                        conn.close()
                    except Exception:
                        pass
                self._local.connections = {}
            return dest

    def list_mbtiles(self):
        mbtiles_dir = self.get_mbtiles_dir()
        files = []
        if os.path.exists(mbtiles_dir):
            for f in os.listdir(mbtiles_dir):
                if is_mbtiles_filename(f):
                    full_path = os.path.join(mbtiles_dir, f)
                    stats = os.stat(full_path)
                    files.append(
                        {
                            "name": f,
                            "size": stats.st_size,
                            "mtime": stats.st_mtime,
                            "is_active": full_path == self.get_offline_path(),
                        },
                    )
        return sorted(files, key=lambda x: x["mtime"], reverse=True)

    def delete_mbtiles(self, filename):
        mbtiles_dir = self.get_mbtiles_dir()
        safe_name = os.path.basename(filename)
        file_path = os.path.join(mbtiles_dir, safe_name)
        if not is_path_within_dir(file_path, mbtiles_dir):
            return False
        if os.path.exists(file_path) and is_mbtiles_filename(file_path):
            if file_path == self.get_offline_path():
                self.config.map_offline_path.set(None)
                self.config.map_offline_enabled.set(False)
            if (
                hasattr(self._local, "connections")
                and file_path in self._local.connections
            ):
                try:
                    self._local.connections[file_path].close()
                except Exception:
                    pass
                del self._local.connections[file_path]
            os.remove(file_path)
            self._metadata_cache = None
            return True
        return False

    def get_metadata(self):
        path = self.get_offline_path()
        if not path or not os.path.exists(path):
            return None

        if self._metadata_cache and self._metadata_cache.get("path") == path:
            return self._metadata_cache

        conn = self.get_connection(path)
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, value FROM metadata")
            rows = cursor.fetchall()
            metadata = {row["name"]: row["value"] for row in rows}
            metadata["path"] = path

            # Basic validation: ensure it's raster (format is not pbf)
            if metadata.get("format") == "pbf":
                RNS.log(
                    "MBTiles file is in vector (PBF) format, which is not supported.",
                    RNS.LOG_ERROR,
                )
                return None

            self._metadata_cache = metadata
            return metadata
        except Exception as e:
            RNS.log(f"Error reading MBTiles metadata: {e}", RNS.LOG_ERROR)
            return None

    def get_tile(self, z, x, y):
        path = self.get_offline_path()
        if not path or not os.path.exists(path):
            return None

        conn = self.get_connection(path)
        if not conn:
            return None

        try:
            # MBTiles uses TMS tiling scheme (y is flipped)
            tms_y = (1 << z) - 1 - y

            cursor = conn.cursor()
            cursor.execute(
                "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
                (z, x, tms_y),
            )
            row = cursor.fetchone()
            if row:
                return row["tile_data"]

            return None
        except Exception as e:
            RNS.log(f"Error reading MBTiles tile {z}/{x}/{y}: {e}", RNS.LOG_ERROR)
            return None

    def count_export_tiles(self, bbox, min_zoom, max_zoom):
        return sum(
            1 for _ in self._iter_export_tiles_for_bbox(bbox, min_zoom, max_zoom)
        )

    def start_export(self, export_id, bbox, min_zoom, max_zoom, name="Exported Map"):
        """Start downloading tiles and creating an MBTiles file in a background thread."""
        thread = threading.Thread(
            target=self._run_export,
            args=(export_id, bbox, min_zoom, max_zoom, name),
            daemon=True,
        )
        self._export_progress[export_id] = {
            "status": "starting",
            "progress": 0,
            "total": 0,
            "current": 0,
            "start_time": time.time(),
        }
        thread.start()
        self.prune_export_records()
        return export_id

    def get_export_status(self, export_id):
        return self._export_progress.get(export_id)

    def prune_export_records(self) -> int:
        terminal = [
            export_id
            for export_id, entry in self._export_progress.items()
            if entry.get("status") in TERMINAL_EXPORT_STATUSES
        ]
        overflow = len(terminal) - MAX_EXPORT_RECORDS
        if overflow <= 0:
            return 0
        ranked = sorted(
            terminal,
            key=lambda eid: float(self._export_progress[eid].get("start_time") or 0.0),
        )
        dropped = 0
        for export_id in ranked[:overflow]:
            if self._export_progress.pop(export_id, None) is not None:
                dropped += 1
            self._export_cancelled.discard(export_id)
        return dropped

    def cancel_export(self, export_id):
        if export_id in self._export_progress:
            self._export_cancelled.add(export_id)
            # If it's already failed or completed, just clean up
            status = self._export_progress[export_id].get("status")
            if status in ["completed", "failed"]:
                file_path = self._export_progress[export_id].get("file_path")
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                del self._export_progress[export_id]
                if export_id in self._export_cancelled:
                    self._export_cancelled.remove(export_id)
            return True
        return False

    def _run_export(self, export_id, bbox, min_zoom, max_zoom, name):
        min_lon, min_lat, max_lon, max_lat = bbox
        tiles_to_download = list(
            self._iter_export_tiles_for_bbox(bbox, min_zoom, max_zoom),
        )

        total_tiles = len(tiles_to_download)
        self._export_progress[export_id]["total"] = total_tiles
        self._export_progress[export_id]["status"] = "downloading"

        dest_path = os.path.join(self.storage_dir, f"export_{export_id}.mbtiles")

        conn = None
        try:
            conn = sqlite3.connect(dest_path)
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS metadata (name text, value text)",
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)",
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS tile_index ON tiles (zoom_level, tile_column, tile_row)",
            )

            metadata = [
                ("name", name),
                ("type", "baselayer"),
                ("version", "1.1"),
                ("description", f"Exported from MeshChatX on {time.ctime()}"),
                ("format", "png"),
                ("bounds", f"{min_lon},{min_lat},{max_lon},{max_lat}"),
            ]
            cursor.executemany("INSERT INTO metadata VALUES (?, ?)", metadata)
            conn.commit()

            tile_server_url = self.config.map_tile_server_url.get()
            asyncio.run(
                self._export_download_tiles(
                    export_id,
                    tiles_to_download,
                    tile_server_url,
                    conn,
                    cursor,
                    total_tiles,
                ),
            )

            if export_id in self._export_cancelled:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                if export_id in self._export_progress:
                    del self._export_progress[export_id]
                self._export_cancelled.remove(export_id)
                return

            self._export_progress[export_id]["status"] = "completed"
            self._export_progress[export_id]["file_path"] = dest_path
            self.prune_export_records()

        except Exception as e:
            RNS.log(f"Map export failed: {e}", RNS.LOG_ERROR)
            self._export_progress[export_id]["status"] = "failed"
            self._export_progress[export_id]["error"] = str(e)
            if os.path.exists(dest_path):
                os.remove(dest_path)
            self.prune_export_records()
        finally:
            if conn is not None:
                conn.close()

    async def _export_download_tiles(
        self,
        export_id,
        tiles_to_download,
        tile_server_url,
        conn,
        cursor,
        total_tiles,
    ):
        sem = asyncio.Semaphore(10)
        timeout = aiohttp.ClientTimeout(total=15)
        headers = {"User-Agent": "MeshChatX/1.0 MapExporter"}
        connector = aiohttp.TCPConnector(limit=10)

        batch_size = 50
        batch_data = []
        current_count = 0

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
        ) as session:

            async def download_tile(tile_coords):
                if export_id in self._export_cancelled:
                    return None

                z, x, y = tile_coords
                tile_url = (
                    tile_server_url.replace("{z}", str(z))
                    .replace("{x}", str(x))
                    .replace("{y}", str(y))
                    .replace("{r}", "")
                )

                await asyncio.sleep(0.02)

                try:
                    async with sem:
                        async with session.get(tile_url, headers=headers) as response:
                            if response.status == 200:
                                data = await response.read()
                                tms_y = (1 << z) - 1 - y
                                return (z, x, tms_y, data)
                except Exception as e:
                    RNS.log(
                        f"Export failed to download tile {z}/{x}/{y}: {e}",
                        RNS.LOG_ERROR,
                    )
                return None

            tasks = [
                asyncio.create_task(download_tile(tile)) for tile in tiles_to_download
            ]

            for coro in asyncio.as_completed(tasks):
                if export_id in self._export_cancelled:
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    break

                result = await coro
                if result:
                    batch_data.append(result)

                current_count += 1

                if current_count % 5 == 0 or current_count == total_tiles:
                    self._export_progress[export_id]["current"] = current_count
                    self._export_progress[export_id]["progress"] = int(
                        (current_count / total_tiles) * 100,
                    )

                if len(batch_data) >= batch_size or (
                    current_count == total_tiles and batch_data
                ):
                    try:
                        cursor.executemany(
                            "INSERT INTO tiles VALUES (?, ?, ?, ?)",
                            batch_data,
                        )
                        conn.commit()
                        batch_data = []
                    except Exception as e:
                        RNS.log(f"Failed to insert map tiles: {e}", RNS.LOG_ERROR)

    def _lonlat_to_tile(self, lon, lat, zoom):
        lat = max(-85.05112878, min(85.05112878, lat))
        lat_rad = math.radians(lat)
        n = 1 << zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int(
            (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
            / 2.0
            * n,
        )
        x = ((x % n) + n) % n
        y = max(0, min(n - 1, y))
        return x, y

    def _tile_x_for_min(self, lon, zoom):
        n = 1 << zoom
        x = int((lon + 180.0) / 360.0 * n)
        return ((x % n) + n) % n

    def _tile_x_for_max(self, lon, zoom):
        n = 1 << zoom
        x = int((lon + 180.0 - 1e-9) / 360.0 * n)
        return ((x % n) + n) % n

    def _tile_y(self, lat, zoom):
        lat = max(-85.05112878, min(85.05112878, lat))
        lat_rad = math.radians(lat)
        n = 1 << zoom
        y = int(
            (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
            / 2.0
            * n,
        )
        return max(0, min(n - 1, y))

    def _iter_export_tiles_for_bbox(self, bbox, min_zoom, max_zoom):
        min_lon, min_lat, max_lon, max_lat = bbox
        lon_span = max_lon - min_lon
        lat_span = max_lat - min_lat
        seen = set()
        for z in range(min_zoom, max_zoom + 1):
            n = 1 << z
            x_min = self._tile_x_for_min(min_lon, z)
            x_max = self._tile_x_for_max(max_lon, z)
            if lon_span >= 360.0 - 1e-9:
                x_ranges = [(0, n - 1)]
            elif lon_span < 0.0:
                x_ranges = [(x_min, n - 1), (0, x_max)]
            else:
                x_ranges = [(x_min, x_max)]
            y_min = self._tile_y(max_lat, z)
            y_max = self._tile_y(min_lat, z)
            if y_min > y_max:
                y_min, y_max = y_max, y_min
            if lat_span >= 180.0 - 1e-9:
                y_min, y_max = 0, n - 1
            for xs, xe in x_ranges:
                if xs > xe:
                    continue
                for x in range(xs, xe + 1):
                    for y in range(y_min, y_max + 1):
                        key = (z, x, y)
                        if key not in seen:
                            seen.add(key)
                            yield key

    def close(self):
        if hasattr(self._local, "connections"):
            for conn in self._local.connections.values():
                conn.close()
            self._local.connections = {}
        self._metadata_cache = None
