# SPDX-License-Identifier: 0BSD

import RNS


class RNPathHandler:
    def __init__(self, reticulum_instance: RNS.Reticulum | None):
        self.reticulum = reticulum_instance

    def get_path_table(
        self,
        max_hops: int | None = None,
        search: str | None = None,
        interface: str | None = None,
        hops: int | None = None,
        page: int = 1,
        limit: int = 0,
        raw_table: list | None = None,
    ):
        if raw_table is None:
            table = self.reticulum.get_path_table(max_hops=max_hops)
        else:
            table = raw_table
        formatted_table = []
        for entry in table:
            # Get additional data directly from Transport.path_table if available
            # to provide more stats as requested.
            dst_hash = entry["hash"]
            if isinstance(dst_hash, str):
                try:
                    dst_hash = bytes.fromhex(dst_hash)
                except ValueError:
                    continue
            announce_hash = None
            state = RNS.Transport.STATE_UNKNOWN

            if raw_table is None and dst_hash in RNS.Transport.path_table:
                pt_entry = RNS.Transport.path_table[dst_hash]
                if len(pt_entry) > 6:
                    announce_hash = pt_entry[6].hex() if pt_entry[6] else None

            if raw_table is None and dst_hash in RNS.Transport.path_states:
                state = RNS.Transport.path_states[dst_hash]
            elif "state" in entry:
                state = entry.get("state", state)

            via = entry.get("via")
            if isinstance(via, (bytes, bytearray)):
                via_hex = via.hex()
            elif isinstance(via, str):
                via_hex = via
            else:
                via_hex = ""

            # Filtering
            if search:
                search_l = search.lower()
                hash_str = dst_hash.hex().lower()
                via_str = via_hex.lower()
                if search_l not in hash_str and search_l not in via_str:
                    continue

            if interface and entry.get("interface") != interface:
                continue

            if hops is not None and entry.get("hops") != hops:
                continue

            formatted_table.append(
                {
                    "hash": dst_hash.hex(),
                    "hops": entry.get("hops"),
                    "via": via_hex,
                    "interface": entry.get("interface"),
                    "expires": entry.get("expires"),
                    "timestamp": entry.get("timestamp"),
                    "announce_hash": announce_hash,
                    "state": state,
                },
            )

        # Sort: Responsive first, then by hops, then by interface
        formatted_table.sort(
            key=lambda e: (
                0 if e["state"] == RNS.Transport.STATE_RESPONSIVE else 1,
                e["hops"] if e["hops"] is not None else 999,
                e["interface"] or "",
            ),
        )

        total = len(formatted_table)
        responsive_count = len(
            [
                e
                for e in formatted_table
                if e["state"] == RNS.Transport.STATE_RESPONSIVE
            ],
        )
        unresponsive_count = len(
            [
                e
                for e in formatted_table
                if e["state"] == RNS.Transport.STATE_UNRESPONSIVE
            ],
        )

        # Pagination
        if limit > 0:
            start = (page - 1) * limit
            end = start + limit
            formatted_table = formatted_table[start:end]

        return {
            "table": formatted_table,
            "total": total,
            "responsive": responsive_count,
            "unresponsive": unresponsive_count,
            "page": page,
            "limit": limit,
        }

    def get_rate_table(self, raw_table: list | None = None):
        if raw_table is None:
            table = self.reticulum.get_rate_table()
        else:
            table = raw_table
        formatted_table = []
        for entry in table:
            entry_hash = entry.get("hash")
            if isinstance(entry_hash, (bytes, bytearray)):
                hash_hex = entry_hash.hex()
            elif isinstance(entry_hash, str):
                hash_hex = entry_hash
            else:
                continue
            formatted_table.append(
                {
                    "hash": hash_hex,
                    "last": entry.get("last"),
                    "timestamps": entry.get("timestamps"),
                    "rate_violations": entry.get("rate_violations"),
                    "blocked_until": entry.get("blocked_until"),
                },
            )
        return sorted(formatted_table, key=lambda e: e.get("last") or 0)

    def drop_path(self, destination_hash: str) -> bool:
        try:
            dest_bytes = bytes.fromhex(destination_hash)
            return self.reticulum.drop_path(dest_bytes)
        except Exception:
            return False

    def drop_all_paths(self) -> int:
        dropped = 0
        try:
            table = self.reticulum.get_path_table()
            for entry in table:
                try:
                    if self.reticulum.drop_path(entry["hash"]):
                        dropped += 1
                except Exception:
                    continue
        except Exception:
            return dropped
        return dropped

    def drop_all_via(self, transport_instance_hash: str) -> bool:
        if self.reticulum is None:
            return False
        try:
            ti_bytes = bytes.fromhex(transport_instance_hash)
            return bool(self.reticulum.drop_all_via(ti_bytes))
        except Exception:
            return False

    def drop_announce_queues(self):
        self.reticulum.drop_announce_queues()
        return True

    def request_path(self, destination_hash: str):
        try:
            dest_bytes = bytes.fromhex(destination_hash)
            RNS.Transport.request_path(dest_bytes)
            return True
        except Exception:
            return False
