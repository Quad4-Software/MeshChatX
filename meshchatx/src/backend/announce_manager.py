# SPDX-License-Identifier: 0BSD

import base64
import threading
import time

from meshchatx.src.backend.meshchat_utils import normalize_hex_identifier

from .database import Database

MAX_ANNOUNCE_APP_DATA_BYTES = 2048

# How often the deferred announce journal is committed to SQLite in one
# transaction. Backbone announce floods otherwise cost a WAL write plus
# several read queries per announce even when the UI never sees them.
ANNOUNCE_JOURNAL_FLUSH_SECONDS = 30.0

# Safety bound for the in-memory deferred journal. Beyond this, the oldest
# pending entries are dropped; peers simply re-announce later.
ANNOUNCE_JOURNAL_MAX_PENDING = 2000

# How long cached contact/favourite/conversation/block sets stay valid.
# Mutations can force an early rebuild via invalidate_peer_sets().
PEER_SETS_REFRESH_SECONDS = 120.0

_ASPECT_MAX_STORED_KEYS = {
    "lxmf.delivery": "announce_max_stored_lxmf_delivery",
    "nomadnetwork.node": "announce_max_stored_nomadnetwork_node",
    "lxmf.propagation": "announce_max_stored_lxmf_propagation",
    "lxst.telephony": "announce_max_stored_lxmf_delivery",
    "map-data-v1": "announce_max_stored_map_data",
}

_ASPECT_FETCH_LIMIT_KEYS = {
    "lxmf.delivery": "announce_fetch_limit_lxmf_delivery",
    "nomadnetwork.node": "announce_fetch_limit_nomadnetwork_node",
    "lxmf.propagation": "announce_fetch_limit_lxmf_propagation",
    "lxst.telephony": "announce_fetch_limit_lxmf_delivery",
    "map-data-v1": "announce_fetch_limit_map_data",
}

_ASPECT_STORE_ENABLE_KEYS = {
    "lxmf.delivery": "announce_store_lxmf_delivery",
    "lxst.telephony": "announce_store_lxst_telephony",
    "nomadnetwork.node": "announce_store_nomadnetwork_node",
    "lxmf.propagation": "announce_store_lxmf_propagation",
    "map-data-v1": "announce_store_map_data",
}

# Scalar lookup so LIMIT on announces runs before any contacts work.
# An OR JOIN can multiply rows when two contacts match the same announce.
_CONTACT_IMAGE_SQL = (
    "(SELECT c.custom_image FROM contacts c "
    "WHERE c.remote_identity_hash = a.identity_hash "
    "OR c.lxmf_address = a.destination_hash "
    "OR c.lxst_address = a.destination_hash "
    "LIMIT 1)"
)


def _norm_hash(value) -> str:
    """Normalize destination/identity hash input (bytes or hex string)."""
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            return bytes(value).hex()
        except Exception:
            return ""
    return normalize_hex_identifier(value)


class AnnounceManager:
    def __init__(
        self,
        db: Database,
        config=None,
        related_hashes_resolver=None,
        is_blocked_resolver=None,
    ):
        self.db = db
        self.config = config
        self._related_hashes_resolver = related_hashes_resolver
        self._is_blocked_resolver = is_blocked_resolver
        self._peer_sets_lock = threading.RLock()
        self._peer_sets_loaded_at = 0.0
        self._priority_hashes: set = set()
        self._blocked_hashes: set = set()
        self._pending_lock = threading.RLock()
        self._pending: dict = {}
        self._pending_aspects: set = set()
        self._flush_stop = threading.Event()
        self._flush_thread: threading.Thread | None = None

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
            return 2500
        key = _ASPECT_FETCH_LIMIT_KEYS.get(aspect)
        if not key:
            return 2500
        attr = getattr(self.config, key, None)
        if attr is None:
            return 2500
        v = attr.get()
        if v is None or v < 1:
            return 2500
        return min(v, 100_000)

    def is_storing_announce_for_aspect(self, aspect, force_store: bool = False) -> bool:
        if force_store or not self.config:
            return True
        key = _ASPECT_STORE_ENABLE_KEYS.get(aspect)
        if not key:
            return True
        attr = getattr(self.config, key, None)
        if attr is None:
            return True
        return bool(attr.get())

    # ------------------------------------------------------------------
    # Ingress gate and deferred journal
    #
    # Backbone interfaces deliver a constant stream of announces from peers
    # the user has no relationship with. Each used to cost several SQLite
    # reads (block-check fanout, read-back, name/icon lookups) plus a WAL
    # write. classify_announce() answers with cached peer sets so the hot
    # path is a dict lookup; "background" announces go through a deferred
    # journal flushed in a single transaction.
    # ------------------------------------------------------------------

    def start(self):
        """Start the periodic journal flush thread."""
        if self._flush_thread is not None:
            return
        self._flush_stop.clear()
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            name="meshchatx-announce-flush",
            daemon=True,
        )
        self._flush_thread.start()

    def stop(self):
        """Stop the flush thread and commit any pending journal rows."""
        self._flush_stop.set()
        thread = self._flush_thread
        if thread is not None:
            thread.join(timeout=5)
        self._flush_thread = None
        self.flush_pending()

    def _flush_loop(self):
        while not self._flush_stop.wait(ANNOUNCE_JOURNAL_FLUSH_SECONDS):
            try:
                self.flush_pending()
            except Exception as exc:
                print(f"Announce journal flush failed: {exc}")

    def invalidate_peer_sets(self):
        """Force priority/blocked set rebuild on the next classify call."""
        with self._peer_sets_lock:
            self._peer_sets_loaded_at = 0.0

    def classify_announce(self, destination_hash, identity_hash=None) -> str:
        """Return 'blocked', 'priority', or 'background' for an inbound announce.

        'priority' peers are contacts, favourites, and conversation partners:
        they take the full immediate path. 'background' peers are everything
        else: deferred DB write and a slim broadcast. 'blocked' announces
        should be dropped by the caller (fail-closed when the block list
        cannot be evaluated at all).
        """
        dh = _norm_hash(destination_hash)
        ih = _norm_hash(identity_hash)
        self._ensure_peer_sets()
        with self._peer_sets_lock:
            blocked = self._blocked_hashes
            priority = self._priority_hashes
            sets_loaded = self._peer_sets_loaded_at > 0
            if dh in blocked or ih in blocked:
                return "blocked"
            if not sets_loaded:
                # Sets never loaded: evaluate blocking directly and fail
                # closed on error, matching is_destination_blocked semantics.
                if self._is_blocked_resolver is not None:
                    try:
                        if self._is_blocked_resolver(dh):
                            return "blocked"
                    except Exception:
                        return "blocked"
                return "background"
            if dh in priority or ih in priority:
                return "priority"
            return "background"

    def _ensure_peer_sets(self):
        if time.time() - self._peer_sets_loaded_at < PEER_SETS_REFRESH_SECONDS:
            return
        self._reload_peer_sets()

    def _reload_peer_sets(self):
        db = self.db
        priority: set = set()
        blocked: set = set()

        try:
            rows = db.provider.fetchall(
                "SELECT remote_identity_hash, lxmf_address, lxst_address FROM contacts",
            )
            for row in rows or []:
                for key in ("remote_identity_hash", "lxmf_address", "lxst_address"):
                    h = _norm_hash(row.get(key))
                    if h:
                        priority.add(h)
        except Exception:
            pass

        try:
            for row in db.announces.get_favourites() or []:
                h = _norm_hash(row.get("destination_hash"))
                if h:
                    priority.add(h)
        except Exception:
            pass

        try:
            rows = db.provider.fetchall(
                "SELECT DISTINCT peer_hash FROM lxmf_messages "
                "WHERE peer_hash IS NOT NULL",
            )
            for row in rows or []:
                h = _norm_hash(row.get("peer_hash"))
                if h:
                    priority.add(h)
        except Exception:
            pass

        raw_blocked = []
        try:
            misc = getattr(db, "misc", None)
            if misc is not None:
                raw_blocked = [
                    r.get("destination_hash")
                    for r in misc.get_blocked_destinations() or []
                ]
        except Exception:
            # Block list unreadable: leave the sets unloaded so classify
            # falls back to the resolver path, which fails closed like
            # is_destination_blocked. Loading an empty block set here
            # would silently unblock every peer.
            return
        for raw in raw_blocked:
            h = _norm_hash(raw)
            if h:
                blocked.add(h)

        # Expand each blocked hash to the peer's other known hashes once per
        # refresh, instead of fanning out announce lookups per announce.
        resolver = self._related_hashes_resolver
        if resolver is not None:
            for raw in list(blocked):
                try:
                    related = resolver(raw) or []
                except Exception:
                    related = []
                for rel in related:
                    h = _norm_hash(rel)
                    if h:
                        blocked.add(h)

        with self._peer_sets_lock:
            self._priority_hashes = priority
            self._blocked_hashes = blocked
            self._peer_sets_loaded_at = time.time()

    def flush_pending(self):
        """Commit deferred announce rows in a single transaction."""
        with self._pending_lock:
            if not self._pending:
                return
            rows = list(self._pending.values())
            aspects = set(self._pending_aspects)
            self._pending.clear()
            self._pending_aspects.clear()
        try:
            with self.db.provider:
                for data in rows:
                    self.db.announces.upsert_announce(data)
        except Exception as exc:
            print(f"Announce journal flush failed ({len(rows)} rows): {exc}")
        for aspect in aspects:
            try:
                max_stored = self._get_max_stored_for_aspect(aspect)
                if max_stored is not None:
                    self.db.announces.trim_announces_for_aspect(
                        aspect,
                        max_stored,
                    )
            except Exception as exc:
                print(f"Announce trim after flush failed for {aspect}: {exc}")

    def upsert_announce(
        self,
        reticulum,
        identity,
        destination_hash,
        aspect,
        app_data,
        announce_packet_hash,
        force_store: bool = False,
        defer: bool = False,
    ):
        if not self.is_storing_announce_for_aspect(aspect, force_store=force_store):
            return None

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
            # Check length before bytes() so an oversized bytearray or
            # memoryview is rejected without materializing a full copy.
            raw = (
                bytes(app_data)
                if isinstance(app_data, (bytes, bytearray, memoryview))
                and len(app_data) <= MAX_ANNOUNCE_APP_DATA_BYTES
                else None
            )
            if raw is not None:
                data["app_data"] = base64.b64encode(raw).decode("utf-8")

        if defer:
            with self._pending_lock:
                if len(self._pending) >= ANNOUNCE_JOURNAL_MAX_PENDING:
                    # Dicts are insertion ordered; drop the oldest entry.
                    self._pending.pop(next(iter(self._pending)))
                self._pending[data["destination_hash"]] = data
                self._pending_aspects.add(aspect)
            return data

        self.db.announces.upsert_announce(data)

        max_stored = self._get_max_stored_for_aspect(aspect)
        if max_stored is not None:
            self.db.announces.trim_announces_for_aspect(aspect, max_stored)
        return data

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

        sql = f"""
            SELECT a.*, {_CONTACT_IMAGE_SQL} as contact_image
            FROM announces a
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

    def get_announces_for_destination_hashes(
        self,
        destination_hashes,
        aspects=None,
        blocked_identity_hashes=None,
    ):
        """Return announce rows for many destination hashes (visualiser bulk query)."""
        if not destination_hashes:
            return []
        aspect_list = aspects or ["lxmf.delivery", "nomadnetwork.node"]
        hash_list = []
        seen = set()
        for raw in destination_hashes:
            if not isinstance(raw, str):
                continue
            h = raw.lower().strip()
            if not h or h in seen:
                continue
            seen.add(h)
            hash_list.append(h)
        if not hash_list:
            return []

        chunk_size = 400
        out = []
        for aspect in aspect_list:
            if not isinstance(aspect, str) or not aspect:
                continue
            for offset in range(0, len(hash_list), chunk_size):
                chunk = hash_list[offset : offset + chunk_size]
                placeholders = ", ".join(["?"] * len(chunk))
                sql = f"""
                    SELECT a.*, {_CONTACT_IMAGE_SQL} as contact_image
                    FROM announces a
                    WHERE a.aspect = ?
                    AND a.destination_hash IN ({placeholders})
                """
                params = [aspect, *chunk]
                if blocked_identity_hashes:
                    blocked_placeholders = ", ".join(
                        ["?"] * len(blocked_identity_hashes),
                    )
                    sql += f" AND a.identity_hash NOT IN ({blocked_placeholders})"
                    params.extend(blocked_identity_hashes)
                sql += " ORDER BY a.updated_at DESC"
                out.extend(self.db.provider.fetchall(sql, params))
        return out


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
