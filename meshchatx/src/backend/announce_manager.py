import base64

from .database import Database

_ASPECT_LIMIT_KEYS = {
    "lxmf.delivery": "announce_limit_lxmf_delivery",
    "nomadnetwork.node": "announce_limit_nomadnetwork_node",
    "lxmf.propagation": "announce_limit_lxmf_propagation",
}


class AnnounceManager:
    def __init__(self, db: Database, config=None):
        self.db = db
        self.config = config

    def _get_limit_for_aspect(self, aspect):
        key = _ASPECT_LIMIT_KEYS.get(aspect)
        if not key:
            return None
        attr = getattr(self.config, key, None)
        if attr is None:
            return None
        return attr.get()

    def upsert_announce(
        self,
        reticulum,
        identity,
        destination_hash,
        aspect,
        app_data,
        announce_packet_hash,
    ):
        if self.config:
            limit = self._get_limit_for_aspect(aspect)
            if limit is not None and limit >= 0:
                dest_hex = (
                    destination_hash.hex()
                    if isinstance(destination_hash, bytes)
                    else destination_hash
                )
                existing = self.db.announces.get_announce_by_hash(dest_hex)
                if not existing or existing.get("aspect") != aspect:
                    count = self.db.announces.get_announce_count_by_aspect(aspect)
                    if count >= limit:
                        return
        rssi = snr = quality = None
        if announce_packet_hash and reticulum:
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
        limit=500,
        offset=0,
    ):
        sql = """
            SELECT a.*, c.custom_image as contact_image 
            FROM announces a
            LEFT JOIN contacts c ON (
                a.identity_hash = c.remote_identity_hash OR 
                a.destination_hash = c.lxmf_address OR 
                a.destination_hash = c.lxst_address
            )
            WHERE 1=1
        """
        params = []

        if aspect:
            sql += " AND a.aspect = ?"
            params.append(aspect)
        if identity_hash:
            sql += " AND a.identity_hash = ?"
            params.append(identity_hash)
        if destination_hash:
            sql += " AND a.destination_hash = ?"
            params.append(destination_hash)
        if query:
            like_term = f"%{query}%"
            sql += " AND (a.destination_hash LIKE ? OR a.identity_hash LIKE ?)"
            params.extend([like_term, like_term])
        if blocked_identity_hashes:
            placeholders = ", ".join(["?"] * len(blocked_identity_hashes))
            sql += f" AND a.identity_hash NOT IN ({placeholders})"
            params.extend(blocked_identity_hashes)

        sql += " ORDER BY a.updated_at DESC"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        return self.db.provider.fetchall(sql, params)

    def get_filtered_announces_count(
        self,
        aspect=None,
        identity_hash=None,
        destination_hash=None,
        query=None,
        blocked_identity_hashes=None,
    ):
        sql = """
            SELECT COUNT(*) as count
            FROM announces a
            LEFT JOIN contacts c ON (
                a.identity_hash = c.remote_identity_hash OR 
                a.destination_hash = c.lxmf_address OR 
                a.destination_hash = c.lxst_address
            )
            WHERE 1=1
        """
        params = []

        if aspect:
            sql += " AND a.aspect = ?"
            params.append(aspect)
        if identity_hash:
            sql += " AND a.identity_hash = ?"
            params.append(identity_hash)
        if destination_hash:
            sql += " AND a.destination_hash = ?"
            params.append(destination_hash)
        if query:
            like_term = f"%{query}%"
            sql += " AND (a.destination_hash LIKE ? OR a.identity_hash LIKE ?)"
            params.extend([like_term, like_term])
        if blocked_identity_hashes:
            placeholders = ", ".join(["?"] * len(blocked_identity_hashes))
            sql += f" AND a.identity_hash NOT IN ({placeholders})"
            params.extend(blocked_identity_hashes)

        result = self.db.provider.fetchone(sql, params)
        return result["count"] if result else 0
