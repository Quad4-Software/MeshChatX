import base64

from .database import Database


class AnnounceManager:
    def __init__(self, db: Database):
        self.db = db

    def upsert_announce(
        self,
        reticulum,
        identity,
        destination_hash,
        aspect,
        app_data,
        announce_packet_hash,
    ):
        # get rssi, snr and signal quality if available
        rssi = reticulum.get_packet_rssi(announce_packet_hash)
        snr = reticulum.get_packet_snr(announce_packet_hash)
        quality = reticulum.get_packet_q(announce_packet_hash)

        # prepare data to insert or update
        data = {
            "destination_hash": destination_hash.hex()
            if isinstance(destination_hash, bytes)
            else destination_hash,
            "aspect": aspect,
            "identity_hash": identity.hash.hex(),
            "identity_public_key": base64.b64encode(identity.get_public_key()).decode(
                "utf-8",
            ),
            "rssi": rssi,
            "snr": snr,
            "quality": quality,
        }

        # only set app data if provided
        if app_data is not None:
            data["app_data"] = base64.b64encode(app_data).decode("utf-8")

        self.db.announces.upsert_announce(data)

    def get_filtered_announces(
        self,
        aspect=None,
        identity_hash=None,
        destination_hash=None,
        query=None,
        blocked_identity_hashes=None,
        limit=None,
        offset=0,
    ):
        sql = "SELECT * FROM announces WHERE 1=1"
        params = []

        if aspect:
            sql += " AND aspect = ?"
            params.append(aspect)
        if identity_hash:
            sql += " AND identity_hash = ?"
            params.append(identity_hash)
        if destination_hash:
            sql += " AND destination_hash = ?"
            params.append(destination_hash)
        if query:
            like_term = f"%{query}%"
            sql += " AND (destination_hash LIKE ? OR identity_hash LIKE ?)"
            params.extend([like_term, like_term])
        if blocked_identity_hashes:
            placeholders = ", ".join(["?"] * len(blocked_identity_hashes))
            sql += f" AND identity_hash NOT IN ({placeholders})"
            params.extend(blocked_identity_hashes)

        sql += " ORDER BY updated_at DESC"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        return self.db.provider.fetchall(sql, params)
