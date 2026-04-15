import base64

from .database import Database

_ASPECT_MAX_STORED_KEYS = {
    "lxmf.delivery": "announce_max_stored_lxmf_delivery",
    "nomadnetwork.node": "announce_max_stored_nomadnetwork_node",
    "lxmf.propagation": "announce_max_stored_lxmf_propagation",
    "lxst.telephony": "announce_max_stored_lxmf_delivery",
}

_ASPECT_FETCH_LIMIT_KEYS = {
    "lxmf.delivery": "announce_fetch_limit_lxmf_delivery",
    "nomadnetwork.node": "announce_fetch_limit_nomadnetwork_node",
    "lxmf.propagation": "announce_fetch_limit_lxmf_propagation",
    "lxst.telephony": "announce_fetch_limit_lxmf_delivery",
}


class AnnounceManager:
    def __init__(self, db: Database, config=None):
        self.db = db
        self.config = config

    def _get_max_stored_for_aspect(self, aspect):
        key = _ASPECT_MAX_STORED_KEYS.get(aspect)
        if not key or not self.config:
            return None
        attr = getattr(self.config, key, None)
        if attr is None:
            return None
        v = attr.get()
        if v is None or v < 1:
            return None
        return min(v, 1_000_000)

    def _get_fetch_limit_for_aspect(self, aspect):
        if not self.config:
            return 500
        key = _ASPECT_FETCH_LIMIT_KEYS.get(aspect)
        if not key:
            return 500
        attr = getattr(self.config, key, None)
        if attr is None:
            return 500
        v = attr.get()
        if v is None or v < 1:
            return 500
        return min(v, 100_000)

    def upsert_announce(
        self,
        reticulum,
        identity,
        destination_hash,
        aspect,
        app_data,
        announce_packet_hash,
    ):
        rssi = snr = quality = None
        if announce_packet_hash and reticulum:
            rssi = reticulum.get_packet_rssi(announce_packet_hash)
            snr = reticulum.get_packet_snr(announce_packet_hash)
            quality = reticulum.get_packet_q(announce_packet_hash)

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

        if app_data is not None:
            data["app_data"] = base64.b64encode(app_data).decode("utf-8")

        self.db.announces.upsert_announce(data)

        max_stored = self._get_max_stored_for_aspect(aspect)
        if max_stored is not None:
            self.db.announces.trim_announces_for_aspect(aspect, max_stored)

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
        if limit is None:
            limit = self._get_fetch_limit_for_aspect(aspect)

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


def filter_announced_dicts_by_search_query(
    items: list[dict],
    search_query: str,
) -> list[dict]:
    """Case-insensitive substring match on display name, hashes, and custom display name."""
    q = search_query.lower()
    return [
        a
        for a in items
        if (
            (a.get("display_name") and q in a["display_name"].lower())
            or (a.get("destination_hash") and q in a["destination_hash"].lower())
            or (a.get("identity_hash") and q in a["identity_hash"].lower())
            or (a.get("custom_display_name") and q in a["custom_display_name"].lower())
        )
    ]
