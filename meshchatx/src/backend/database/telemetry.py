import json
from datetime import UTC, datetime

from .provider import DatabaseProvider


class TelemetryDAO:
    def __init__(self, provider: DatabaseProvider):
        self.provider = provider

    def upsert_telemetry(
        self,
        destination_hash,
        timestamp,
        data,
        received_from=None,
        physical_link=None,
    ):
        now = datetime.now(UTC).isoformat()

        # If physical_link is a dict, convert to json
        if isinstance(physical_link, dict):
            physical_link = json.dumps(physical_link)

        self.provider.execute(
            """
            INSERT INTO lxmf_telemetry (destination_hash, timestamp, data, received_from, physical_link, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(destination_hash, timestamp) DO UPDATE SET 
                data = EXCLUDED.data, 
                received_from = EXCLUDED.received_from,
                physical_link = EXCLUDED.physical_link,
                updated_at = EXCLUDED.updated_at
        """,
            (destination_hash, timestamp, data, received_from, physical_link, now, now),
        )

    def get_latest_telemetry(self, destination_hash):
        return self.provider.fetchone(
            "SELECT * FROM lxmf_telemetry WHERE destination_hash = ? ORDER BY timestamp DESC LIMIT 1",
            (destination_hash,),
        )

    def get_telemetry_history(self, destination_hash, limit=100, offset=0):
        return self.provider.fetchall(
            "SELECT * FROM lxmf_telemetry WHERE destination_hash = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (destination_hash, limit, offset),
        )

    def get_all_latest_telemetry(self):
        # Get the latest telemetry entry for every unique destination_hash
        query = """
            SELECT t1.* FROM lxmf_telemetry t1
            JOIN (
                SELECT destination_hash, MAX(timestamp) as max_ts
                FROM lxmf_telemetry
                GROUP BY destination_hash
            ) t2 ON t1.destination_hash = t2.destination_hash AND t1.timestamp = t2.max_ts
            ORDER BY t1.timestamp DESC
        """
        return self.provider.fetchall(query)

    def delete_telemetry_for_destination(self, destination_hash):
        self.provider.execute(
            "DELETE FROM lxmf_telemetry WHERE destination_hash = ?",
            (destination_hash,),
        )

    def is_tracking(self, destination_hash):
        row = self.provider.fetchone(
            "SELECT is_tracking FROM telemetry_tracking WHERE destination_hash = ?",
            (destination_hash,),
        )
        return bool(row["is_tracking"]) if row else False

    def toggle_tracking(self, destination_hash, is_tracking=None):
        if is_tracking is None:
            is_tracking = not self.is_tracking(destination_hash)

        now = datetime.now(UTC).isoformat()
        self.provider.execute(
            """
            INSERT INTO telemetry_tracking (destination_hash, is_tracking, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(destination_hash) DO UPDATE SET 
                is_tracking = EXCLUDED.is_tracking,
                updated_at = EXCLUDED.updated_at
        """,
            (destination_hash, int(is_tracking), now),
        )
        return is_tracking

    def get_tracked_peers(self):
        return self.provider.fetchall(
            "SELECT * FROM telemetry_tracking WHERE is_tracking = 1",
        )

    def update_last_request_at(self, destination_hash, timestamp=None):
        if timestamp is None:
            import time

            timestamp = time.time()
        self.provider.execute(
            "UPDATE telemetry_tracking SET last_request_at = ? WHERE destination_hash = ?",
            (timestamp, destination_hash),
        )
