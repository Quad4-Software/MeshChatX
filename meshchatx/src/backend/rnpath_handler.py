import RNS


class RNPathHandler:
    def __init__(self, reticulum_instance: RNS.Reticulum):
        self.reticulum = reticulum_instance

    def get_path_table(
        self,
        max_hops: int = None,
        search: str = None,
        interface: str = None,
        hops: int = None,
        page: int = 1,
        limit: int = 0,
    ):
        table = self.reticulum.get_path_table(max_hops=max_hops)
        formatted_table = []
        for entry in table:
            # Get additional data directly from Transport.path_table if available
            # to provide more stats as requested.
            dst_hash = entry["hash"]
            announce_hash = None
            state = RNS.Transport.STATE_UNKNOWN

            if dst_hash in RNS.Transport.path_table:
                pt_entry = RNS.Transport.path_table[dst_hash]
                if len(pt_entry) > 6:
                    announce_hash = pt_entry[6].hex() if pt_entry[6] else None

            if dst_hash in RNS.Transport.path_states:
                state = RNS.Transport.path_states[dst_hash]

            # Filtering
            if search:
                search = search.lower()
                hash_str = entry["hash"].hex().lower()
                via_str = entry["via"].hex().lower()
                if search not in hash_str and search not in via_str:
                    continue

            if interface and entry["interface"] != interface:
                continue

            if hops is not None and entry["hops"] != hops:
                continue

            formatted_table.append(
                {
                    "hash": entry["hash"].hex(),
                    "hops": entry["hops"],
                    "via": entry["via"].hex(),
                    "interface": entry["interface"],
                    "expires": entry["expires"],
                    "timestamp": entry.get("timestamp"),
                    "announce_hash": announce_hash,
                    "state": state,
                }
            )

        # Sort: Responsive first, then by hops, then by interface
        formatted_table.sort(
            key=lambda e: (
                0 if e["state"] == RNS.Transport.STATE_RESPONSIVE else 1,
                e["hops"],
                e["interface"],
            )
        )

        total = len(formatted_table)
        responsive_count = len(
            [e for e in formatted_table if e["state"] == RNS.Transport.STATE_RESPONSIVE]
        )
        unresponsive_count = len(
            [
                e
                for e in formatted_table
                if e["state"] == RNS.Transport.STATE_UNRESPONSIVE
            ]
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

    def get_rate_table(self):
        table = self.reticulum.get_rate_table()
        formatted_table = []
        for entry in table:
            formatted_table.append(
                {
                    "hash": entry["hash"].hex(),
                    "last": entry["last"],
                    "timestamps": entry["timestamps"],
                    "rate_violations": entry["rate_violations"],
                    "blocked_until": entry["blocked_until"],
                }
            )
        return sorted(formatted_table, key=lambda e: e["last"])

    def drop_path(self, destination_hash: str) -> bool:
        try:
            dest_bytes = bytes.fromhex(destination_hash)
            return self.reticulum.drop_path(dest_bytes)
        except Exception:
            return False

    def drop_all_via(self, transport_instance_hash: str) -> bool:
        try:
            ti_bytes = bytes.fromhex(transport_instance_hash)
            return self.reticulum.drop_all_via(ti_bytes)
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
