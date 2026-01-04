import RNS


class RNPathHandler:
    def __init__(self, reticulum_instance: RNS.Reticulum):
        self.reticulum = reticulum_instance

    def get_path_table(self, max_hops: int = None):
        table = self.reticulum.get_path_table(max_hops=max_hops)
        formatted_table = []
        for entry in table:
            formatted_table.append(
                {
                    "hash": entry["hash"].hex(),
                    "hops": entry["hops"],
                    "via": entry["via"].hex(),
                    "interface": entry["interface"],
                    "expires": entry["expires"],
                }
            )
        return sorted(formatted_table, key=lambda e: (e["interface"], e["hops"]))

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
