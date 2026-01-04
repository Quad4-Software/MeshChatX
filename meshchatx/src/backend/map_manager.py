import base64
import concurrent.futures
import math
import os
import sqlite3
import threading
import time

import requests
import RNS

# 1x1 transparent PNG to return when a tile is not found in offline mode
TRANSPARENT_TILE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
)


class MapManager:
    def __init__(self, config_manager, storage_dir):
        self.config = config_manager
        self.storage_dir = storage_dir
        self._local = threading.local()
        self._metadata_cache = None
        self._export_progress = {}
        self._export_cancelled = set()

    def get_connection(self, path):
        if not hasattr(self._local, "connections"):
            self._local.connections = {}

        if path not in self._local.connections:
            if not os.path.exists(path):
                return None
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.connections[path] = conn

        return self._local.connections[path]

    def get_offline_path(self):
        path = self.config.map_offline_path.get()
        if path:
            return path

        # Fallback to default if not set but file exists
        default_path = os.path.join(self.storage_dir, "offline_map.mbtiles")
        if os.path.exists(default_path):
            return default_path

        return None

    def get_mbtiles_dir(self):
        dir_path = self.config.map_mbtiles_dir.get()
        if dir_path and os.path.isdir(dir_path):
            return dir_path
        return self.storage_dir

    def list_mbtiles(self):
        mbtiles_dir = self.get_mbtiles_dir()
        files = []
        if os.path.exists(mbtiles_dir):
            for f in os.listdir(mbtiles_dir):
                if f.endswith(".mbtiles"):
                    full_path = os.path.join(mbtiles_dir, f)
                    stats = os.stat(full_path)
                    files.append(
                        {
                            "name": f,
                            "path": full_path,
                            "size": stats.st_size,
                            "mtime": stats.st_mtime,
                            "is_active": full_path == self.get_offline_path(),
                        },
                    )
        return sorted(files, key=lambda x: x["mtime"], reverse=True)

    def delete_mbtiles(self, filename):
        mbtiles_dir = self.get_mbtiles_dir()
        file_path = os.path.join(mbtiles_dir, filename)
        if os.path.exists(file_path) and file_path.endswith(".mbtiles"):
            if file_path == self.get_offline_path():
                self.config.map_offline_path.set(None)
                self.config.map_offline_enabled.set(False)
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
        return export_id

    def get_export_status(self, export_id):
        return self._export_progress.get(export_id)

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
        # bbox: [min_lon, min_lat, max_lon, max_lat]
        min_lon, min_lat, max_lon, max_lat = bbox

        # collect all tiles to download
        tiles_to_download = []
        zoom_levels = range(min_zoom, max_zoom + 1)
        for z in zoom_levels:
            x1, y1 = self._lonlat_to_tile(min_lon, max_lat, z)
            x2, y2 = self._lonlat_to_tile(max_lon, min_lat, z)
            for x in range(x1, x2 + 1):
                for y in range(y1, y2 + 1):
                    tiles_to_download.append((z, x, y))

        total_tiles = len(tiles_to_download)
        self._export_progress[export_id]["total"] = total_tiles
        self._export_progress[export_id]["status"] = "downloading"

        dest_path = os.path.join(self.storage_dir, f"export_{export_id}.mbtiles")

        try:
            conn = sqlite3.connect(dest_path)
            cursor = conn.cursor()

            # create schema
            cursor.execute("CREATE TABLE metadata (name text, value text)")
            cursor.execute(
                "CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)",
            )
            cursor.execute(
                "CREATE UNIQUE INDEX tile_index on tiles (zoom_level, tile_column, tile_row)",
            )

            # insert metadata
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
            current_count = 0

            # download tiles in parallel
            # using 10 workers for a good balance between speed and being polite
            max_workers = 10

            def download_tile(tile_coords):
                if export_id in self._export_cancelled:
                    return None

                z, x, y = tile_coords
                tile_url = (
                    tile_server_url.replace("{z}", str(z))
                    .replace("{x}", str(x))
                    .replace("{y}", str(y))
                )

                try:
                    # small per-thread delay to avoid overwhelming servers
                    time.sleep(0.02)

                    response = requests.get(
                        tile_url,
                        headers={"User-Agent": "MeshChatX/1.0 MapExporter"},
                        timeout=15,
                    )
                    if response.status_code == 200:
                        # MBTiles uses TMS (y flipped)
                        tms_y = (1 << z) - 1 - y
                        return (z, x, tms_y, response.content)
                except Exception as e:
                    RNS.log(
                        f"Export failed to download tile {z}/{x}/{y}: {e}",
                        RNS.LOG_ERROR,
                    )
                return None

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                future_to_tile = {
                    executor.submit(download_tile, tile): tile
                    for tile in tiles_to_download
                }

                batch_size = 50
                batch_data = []

                for future in concurrent.futures.as_completed(future_to_tile):
                    if export_id in self._export_cancelled:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    result = future.result()
                    if result:
                        batch_data.append(result)

                    current_count += 1

                    # Update progress every few tiles or when batch is ready
                    if current_count % 5 == 0 or current_count == total_tiles:
                        self._export_progress[export_id]["current"] = current_count
                        self._export_progress[export_id]["progress"] = int(
                            (current_count / total_tiles) * 100,
                        )

                    # Write batches to database
                    if len(batch_data) >= batch_size or (
                        current_count == total_tiles and batch_data
                    ):
                        try:
                            cursor.executemany(
                                "INSERT INTO tiles VALUES (?, ?, ?, ?)", batch_data
                            )
                            conn.commit()
                            batch_data = []
                        except Exception as e:
                            RNS.log(f"Failed to insert map tiles: {e}", RNS.LOG_ERROR)

            if export_id in self._export_cancelled:
                conn.close()
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                if export_id in self._export_progress:
                    del self._export_progress[export_id]
                self._export_cancelled.remove(export_id)
                return

            conn.close()
            self._export_progress[export_id]["status"] = "completed"
            self._export_progress[export_id]["file_path"] = dest_path

        except Exception as e:
            RNS.log(f"Map export failed: {e}", RNS.LOG_ERROR)
            self._export_progress[export_id]["status"] = "failed"
            self._export_progress[export_id]["error"] = str(e)
            if os.path.exists(dest_path):
                os.remove(dest_path)

    def _lonlat_to_tile(self, lon, lat, zoom):
        lat_rad = math.radians(lat)
        n = 2.0**zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int(
            (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
            / 2.0
            * n,
        )
        return x, y

    def close(self):
        if hasattr(self._local, "connections"):
            for conn in self._local.connections.values():
                conn.close()
            self._local.connections = {}
        self._metadata_cache = None
