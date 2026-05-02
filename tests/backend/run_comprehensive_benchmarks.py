# SPDX-License-Identifier: 0BSD

import json
import os
import random
import secrets
import shutil
import sys
import tempfile
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

from meshchatx.src.backend.database import Database  # noqa: E402
from meshchatx.src.backend.database.access_attempts import (  # noqa: E402
    AccessAttemptsDAO,
    user_agent_hash,
)
from meshchatx.src.backend.database.contacts import ContactsDAO  # noqa: E402
from meshchatx.src.backend.database.map_drawings import MapDrawingsDAO  # noqa: E402
from meshchatx.src.backend.database.telephone import TelephoneDAO  # noqa: E402
from meshchatx.src.backend.database.voicemails import VoicemailDAO  # noqa: E402
from meshchatx.src.backend.identity_manager import IdentityManager  # noqa: E402
from tests.backend.benchmarking_utils import (  # noqa: E402
    benchmark,
    get_memory_usage_mb,
)


class BackendBenchmarker:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "benchmark.db")
        self.db = Database(self.db_path)
        self.db.initialize()
        self.results = []
        self.my_hash = secrets.token_hex(16)

    def cleanup(self):
        self.db.close()
        shutil.rmtree(self.temp_dir)

    def run_all(self, extreme=False, json_output_path=None):
        print(f"\n{'=' * 20} BACKEND BENCHMARKING START {'=' * 20}")
        print(f"Mode: {'EXTREME (Breaking Space)' if extreme else 'Standard'}")
        print(f"Base Memory: {get_memory_usage_mb():.2f} MB")

        self.bench_db_initialization()

        if extreme:
            self.bench_extreme_message_flood()
            self.bench_extreme_announce_flood()
            self.bench_extreme_identity_bloat()
        else:
            self.bench_message_operations()
            self.bench_announce_operations()
            self.bench_identity_operations()

        self.bench_telephony_operations()
        self.bench_contact_operations()
        self.bench_config_operations()
        self.bench_telemetry_operations()
        self.bench_debug_log_operations()
        self.bench_map_drawing_operations()
        self.bench_voicemail_operations()
        self.bench_access_attempt_operations()
        self.bench_misc_operations()

        self.print_summary(json_output_path=json_output_path)

    def bench_extreme_message_flood(self):
        """Insert 100,000 messages with large randomized content."""
        peer_hashes = [secrets.token_hex(16) for _ in range(200)]
        total_messages = 100000
        batch_size = 5000

        @benchmark("EXTREME: 100k Message Flood", iterations=1)
        def run_extreme_flood():
            for b in range(0, total_messages, batch_size):
                with self.db.provider:
                    for i in range(batch_size):
                        peer_hash = random.choice(peer_hashes)
                        msg = {
                            "hash": secrets.token_hex(16),
                            "source_hash": peer_hash,
                            "destination_hash": self.my_hash,
                            "peer_hash": peer_hash,
                            "state": "delivered",
                            "progress": 1.0,
                            "is_incoming": True,
                            "method": "direct",
                            "delivery_attempts": 1,
                            "title": f"Extreme Msg {b + i}",
                            "content": secrets.token_bytes(
                                1024,
                            ).hex(),  # 2KB hex string
                            "fields": json.dumps({"test": "data" * 10}),
                            "timestamp": time.time() - (total_messages - (b + i)),
                            "rssi": -random.randint(30, 120),
                            "snr": random.uniform(-20, 15),
                            "quality": random.randint(0, 3),
                            "is_spam": 0,
                        }
                        self.db.messages.upsert_lxmf_message(msg)
                print(
                    f"  Progress: {b + batch_size}/{total_messages} messages inserted...",
                )

        @benchmark("EXTREME: Search 100k Messages (Wildcard)", iterations=5)
        def run_extreme_search():
            return self.db.messages.get_conversation_messages(
                peer_hashes[0],
                limit=100,
                offset=50000,
            )

        _, res_flood = run_extreme_flood()
        self.results.append(res_flood)

        _, res_search = run_extreme_search()
        self.results.append(res_search)

    def bench_extreme_announce_flood(self):
        """Insert 50,000 unique announces and perform heavy filtering."""
        total = 50000
        batch = 5000

        @benchmark("EXTREME: 50k Announce Flood", iterations=1)
        def run_ann_flood():
            for b in range(0, total, batch):
                with self.db.provider:
                    for i in range(batch):
                        data = {
                            "destination_hash": secrets.token_hex(16),
                            "aspect": random.choice(
                                ["lxmf.delivery", "lxst.telephony", "group.chat"],
                            ),
                            "identity_hash": secrets.token_hex(16),
                            "identity_public_key": secrets.token_hex(32),
                            "app_data": secrets.token_hex(128),
                            "rssi": -random.randint(50, 100),
                            "snr": 5.0,
                            "quality": 3,
                        }
                        self.db.announces.upsert_announce(data)
                print(f"  Progress: {b + batch}/{total} announces inserted...")

        @benchmark("EXTREME: Filter 50k Announces (Complex)", iterations=10)
        def run_ann_filter():
            return self.db.announces.get_filtered_announces(
                aspect="lxmf.delivery",
                limit=100,
                offset=25000,
            )

        _, res_flood = run_ann_flood()
        self.results.append(res_flood)

        _, res_filter = run_ann_filter()
        self.results.append(res_filter)

    def bench_extreme_identity_bloat(self):
        """Create 1,000 identities and list them."""
        manager = IdentityManager(self.temp_dir)

        @benchmark("EXTREME: Create 1000 Identities", iterations=1)
        def run_id_bloat():
            for i in range(1000):
                manager.create_identity(f"Extreme ID {i}")
                if i % 100 == 0:
                    print(f"  Progress: {i}/1000 identities...")

        @benchmark("EXTREME: List 1000 Identities", iterations=5)
        def run_id_list():
            return manager.list_identities()

        _, res_bloat = run_id_bloat()
        self.results.append(res_bloat)

        _, res_list = run_id_list()
        self.results.append(res_list)

    def bench_db_initialization(self):
        @benchmark("Database Initialization", iterations=5)
        def run():
            tmp_db_path = os.path.join(
                self.temp_dir,
                f"init_test_{random.randint(0, 1000)}.db",
            )
            db = Database(tmp_db_path)
            db.initialize()
            db.close()
            os.remove(tmp_db_path)

        _, res = run()
        self.results.append(res)

    def bench_message_operations(self):
        peer_hashes = [secrets.token_hex(16) for _ in range(50)]

        @benchmark("Message Upsert (Batch of 100)", iterations=10)
        def upsert_batch():
            with self.db.provider:
                for i in range(100):
                    peer_hash = random.choice(peer_hashes)
                    msg = {
                        "hash": secrets.token_hex(16),
                        "source_hash": peer_hash,
                        "destination_hash": self.my_hash,
                        "peer_hash": peer_hash,
                        "state": "delivered",
                        "progress": 1.0,
                        "is_incoming": True,
                        "method": "direct",
                        "delivery_attempts": 1,
                        "title": f"Bench Msg {i}",
                        "content": "X" * 256,
                        "fields": "{}",
                        "timestamp": time.time(),
                        "rssi": -50,
                        "snr": 5.0,
                        "quality": 3,
                        "is_spam": 0,
                    }
                    self.db.messages.upsert_lxmf_message(msg)

        @benchmark("Get 100 Conversations List", iterations=10)
        def get_convs():
            return self.db.messages.get_conversations()

        @benchmark("Get Messages for Conversation (offset 500)", iterations=20)
        def get_messages():
            return self.db.messages.get_conversation_messages(
                peer_hashes[0],
                limit=50,
                offset=500,
            )

        _, res = upsert_batch()
        self.results.append(res)

        # Seed some messages for retrieval benchmarks
        for _ in range(10):
            upsert_batch()

        _, res = get_convs()
        self.results.append(res)

        _, res = get_messages()
        self.results.append(res)

    def bench_announce_operations(self):
        @benchmark("Announce Upsert (Batch of 100)", iterations=10)
        def upsert_announces():
            with self.db.provider:
                for i in range(100):
                    data = {
                        "destination_hash": secrets.token_hex(16),
                        "aspect": "lxmf.delivery",
                        "identity_hash": secrets.token_hex(16),
                        "identity_public_key": "pubkey",
                        "app_data": "bench data",
                        "rssi": -50,
                        "snr": 5.0,
                        "quality": 3,
                    }
                    self.db.announces.upsert_announce(data)

        @benchmark("Filtered Announce Retrieval", iterations=20)
        def get_announces():
            return self.db.announces.get_filtered_announces(limit=50)

        @benchmark("Trim Announces for Aspect", iterations=20)
        def trim_announces():
            return self.db.announces.trim_announces_for_aspect("lxmf.delivery", 500)

        _, res = upsert_announces()
        self.results.append(res)
        _, res = get_announces()
        self.results.append(res)
        _, res = trim_announces()
        self.results.append(res)

    def bench_identity_operations(self):
        manager = IdentityManager(self.temp_dir)

        @benchmark("Create Identity", iterations=5)
        def create_id():
            return manager.create_identity(f"Bench {random.randint(0, 1000)}")

        @benchmark("List 50 Identities", iterations=10)
        def list_ids():
            return manager.list_identities()

        # Seed some identities
        for i in range(50):
            create_id()

        _, res = create_id()
        self.results.append(res)
        _, res = list_ids()
        self.results.append(res)

    def bench_telephony_operations(self):
        dao = TelephoneDAO(self.db.provider)

        @benchmark("Log Telephone Call", iterations=20)
        def log_call():
            dao.add_call_history(
                remote_identity_hash=secrets.token_hex(16),
                remote_identity_name="Bench Peer",
                is_incoming=False,
                status="completed",
                duration_seconds=120,
                timestamp=time.time(),
            )

        _, res = log_call()
        self.results.append(res)

    def bench_contact_operations(self):
        dao = ContactsDAO(self.db.provider)
        hashes = [secrets.token_hex(16) for _ in range(200)]

        @benchmark("Contact Upsert (Batch of 100)", iterations=10)
        def upsert_contacts():
            with self.db.provider:
                for i in range(100):
                    dao.add_contact(
                        name=f"Peer {i}",
                        remote_identity_hash=random.choice(hashes),
                        lxmf_address=secrets.token_hex(16),
                    )

        @benchmark("Get Contacts List", iterations=20)
        def list_contacts():
            return dao.get_contacts(limit=100)

        @benchmark("Contact Search (LIKE query)", iterations=20)
        def search_contacts():
            return dao.get_contacts(search="Peer 1", limit=50)

        @benchmark("Get Contact by Identity Hash", iterations=20)
        def lookup_contact():
            return dao.get_contact_by_identity_hash(random.choice(hashes))

        _, res = upsert_contacts()
        self.results.append(res)
        for _ in range(5):
            upsert_contacts()
        _, res = list_contacts()
        self.results.append(res)
        _, res = search_contacts()
        self.results.append(res)
        _, res = lookup_contact()
        self.results.append(res)

    def bench_config_operations(self):
        @benchmark("Config Set (50 keys)", iterations=20)
        def set_config():
            with self.db.provider:
                for i in range(50):
                    self.db.config.set(
                        f"bench_key_{i}", f"value_{secrets.token_hex(4)}"
                    )

        @benchmark("Config Get (50 keys)", iterations=20)
        def get_config():
            for i in range(50):
                self.db.config.get(f"bench_key_{i}")

        _, res = set_config()
        self.results.append(res)
        _, res = get_config()
        self.results.append(res)

    def bench_telemetry_operations(self):
        peers = [secrets.token_hex(16) for _ in range(50)]

        @benchmark("Telemetry Upsert (Batch of 100)", iterations=10)
        def upsert_telemetry():
            with self.db.provider:
                for _ in range(100):
                    self.db.telemetry.upsert_telemetry(
                        destination_hash=random.choice(peers),
                        timestamp=time.time() - random.randint(0, 3600),
                        data='{"battery":85,"temp":22}',
                        received_from=secrets.token_hex(16),
                    )

        @benchmark("Get All Latest Telemetry", iterations=20)
        def get_all_latest():
            return self.db.telemetry.get_all_latest_telemetry()

        @benchmark("Get Telemetry History (single peer)", iterations=20)
        def get_history():
            return self.db.telemetry.get_telemetry_history(peers[0], limit=50)

        _, res = upsert_telemetry()
        self.results.append(res)
        for _ in range(5):
            upsert_telemetry()
        _, res = get_all_latest()
        self.results.append(res)
        _, res = get_history()
        self.results.append(res)

    def bench_debug_log_operations(self):
        modules = ["meshchat", "database", "lxmf", "reticulum", "api"]

        @benchmark("Debug Log Insert (Batch of 100)", iterations=10)
        def insert_logs():
            with self.db.provider:
                for i in range(100):
                    self.db.debug_logs.insert_log(
                        level="INFO",
                        module=random.choice(modules),
                        message=f"bench log message {i}: " + secrets.token_hex(16),
                    )

        @benchmark("Get Debug Logs (filtered)", iterations=20)
        def get_logs():
            return self.db.debug_logs.get_logs(limit=100, module="meshchat")

        @benchmark("Debug Log Cleanup (trim to 10k)", iterations=5)
        def cleanup_logs():
            return self.db.debug_logs.cleanup_old_logs(max_logs=10000)

        _, res = insert_logs()
        self.results.append(res)
        for _ in range(10):
            insert_logs()
        _, res = get_logs()
        self.results.append(res)
        _, res = cleanup_logs()
        self.results.append(res)

    def bench_map_drawing_operations(self):
        dao = MapDrawingsDAO(self.db.provider)
        identity_hashes = [secrets.token_hex(16) for _ in range(10)]
        drawing_data = (
            '{"type":"FeatureCollection","features":['
            + ",".join(
                [
                    '{"type":"Feature","geometry":{"type":"Point","coordinates":[0,0]},"properties":{}}'
                ]
                * 20
            )
            + "]}"
        )

        @benchmark("Map Drawing Upsert", iterations=20)
        def upsert_drawing():
            with self.db.provider:
                dao.upsert_drawing(
                    identity_hash=random.choice(identity_hashes),
                    name=f"route_{random.randint(0, 10)}",
                    data=drawing_data,
                )

        @benchmark("Get Map Drawings for Identity", iterations=20)
        def get_drawings():
            return dao.get_drawings(random.choice(identity_hashes))

        _, res = upsert_drawing()
        self.results.append(res)
        for _ in range(10):
            upsert_drawing()
        _, res = get_drawings()
        self.results.append(res)

    def bench_voicemail_operations(self):
        dao = VoicemailDAO(self.db.provider)
        peers = [secrets.token_hex(16) for _ in range(20)]

        @benchmark("Voicemail Add (Batch of 50)", iterations=10)
        def add_voicemails():
            with self.db.provider:
                for i in range(50):
                    dao.add_voicemail(
                        remote_identity_hash=random.choice(peers),
                        remote_identity_name=f"Peer {i}",
                        filename=f"vm_{secrets.token_hex(8)}.opus",
                        duration_seconds=random.randint(5, 300),
                        timestamp=time.time() - random.randint(0, 86400),
                    )

        @benchmark("Get Voicemails List", iterations=20)
        def get_voicemails():
            return dao.get_voicemails(limit=50)

        @benchmark("Get Voicemail Unread Count", iterations=20)
        def unread_count():
            return dao.get_unread_count()

        _, res = add_voicemails()
        self.results.append(res)
        for _ in range(3):
            add_voicemails()
        _, res = get_voicemails()
        self.results.append(res)
        _, res = unread_count()
        self.results.append(res)

    def bench_access_attempt_operations(self):
        dao = AccessAttemptsDAO(self.db.provider)
        identity_hash = secrets.token_hex(16)
        ips = [f"192.168.1.{i}" for i in range(50)]
        ua = "Mozilla/5.0 (bench)"
        ua_h = user_agent_hash(ua)

        @benchmark("Access Attempt Insert (Batch of 100)", iterations=10)
        def insert_attempts():
            with self.db.provider:
                for _ in range(100):
                    dao.insert(
                        identity_hash=identity_hash,
                        client_ip=random.choice(ips),
                        user_agent=ua,
                        path="/api/v1/auth/login",
                        method="POST",
                        outcome=random.choice(["success", "failed_password"]),
                    )

        @benchmark("Access Attempt Count by IP", iterations=20)
        def count_by_ip():
            return dao.count_login_attempts_ip(
                client_ip=random.choice(ips),
                path="/api/v1/auth/login",
                since_ts=time.time() - 60,
            )

        @benchmark("Lockout Failure Count (correlated subquery)", iterations=20)
        def count_lockout():
            return dao.count_lockout_failures(
                identity_hash=identity_hash,
                client_ip=random.choice(ips),
                since_ts=time.time() - 900,
            )

        @benchmark("Upsert Trusted Client", iterations=20)
        def upsert_trusted():
            with self.db.provider:
                dao.upsert_trusted(identity_hash, random.choice(ips), ua_h)

        _, res = insert_attempts()
        self.results.append(res)
        for _ in range(10):
            insert_attempts()
        _, res = count_by_ip()
        self.results.append(res)
        _, res = count_lockout()
        self.results.append(res)
        _, res = upsert_trusted()
        self.results.append(res)

    def bench_misc_operations(self):
        dest_hashes = [secrets.token_hex(16) for _ in range(100)]

        @benchmark("Blocked Destination Add + Check (hot path)", iterations=20)
        def blocked_dest_roundtrip():
            h = random.choice(dest_hashes)
            with self.db.provider:
                self.db.misc.add_blocked_destination(h)
            return self.db.misc.is_destination_blocked(h)

        @benchmark("Get Blocked Destinations List", iterations=20)
        def get_blocked():
            return self.db.misc.get_blocked_destinations()

        @benchmark("User Icon Upsert + Lookup", iterations=20)
        def icon_roundtrip():
            h = random.choice(dest_hashes)
            with self.db.provider:
                self.db.misc.update_lxmf_user_icon(h, "person", "#ffffff", "#000000")
            return self.db.misc.get_user_icon(h)

        @benchmark("User Icons Multi-Lookup (50 hashes)", iterations=20)
        def icon_multi_lookup():
            sample = random.sample(dest_hashes, min(50, len(dest_hashes)))
            return self.db.misc.get_user_icons(sample)

        @benchmark("Notification Add + Unread Count", iterations=20)
        def notification_roundtrip():
            with self.db.provider:
                self.db.misc.add_notification(
                    notification_type="message",
                    remote_hash=random.choice(dest_hashes),
                    title="bench",
                    content="bench notification content",
                )
            return self.db.misc.get_unread_notification_count()

        for _ in range(50):
            with self.db.provider:
                self.db.misc.add_blocked_destination(random.choice(dest_hashes))
            with self.db.provider:
                self.db.misc.update_lxmf_user_icon(
                    random.choice(dest_hashes), "person", "#fff", "#000"
                )

        _, res = blocked_dest_roundtrip()
        self.results.append(res)
        _, res = get_blocked()
        self.results.append(res)
        _, res = icon_roundtrip()
        self.results.append(res)
        _, res = icon_multi_lookup()
        self.results.append(res)
        _, res = notification_roundtrip()
        self.results.append(res)

    def print_summary(self, json_output_path=None):
        print(f"\n{'=' * 20} BENCHMARK SUMMARY {'=' * 20}")
        print(f"{'Benchmark Name':40} | {'Avg Time':10} | {'Mem Delta':10}")
        print(f"{'-' * 40}-|-{'-' * 10}-|-{'-' * 10}")
        for r in self.results:
            print(
                f"{r.name:40} | {r.duration_ms:8.2f} ms | {r.memory_delta_mb:8.2f} MB",
            )
        print(f"{'=' * 59}")
        print(f"Final Memory Usage: {get_memory_usage_mb():.2f} MB")

        if json_output_path:
            import json as _json

            entries = [
                {
                    "name": r.name,
                    "unit": "ms",
                    "value": round(r.duration_ms, 3),
                    "extra": f"Memory delta: {r.memory_delta_mb:.2f} MB",
                }
                for r in self.results
            ]
            with open(json_output_path, "w") as f:
                _json.dump(entries, f, indent=2)
            print(f"Benchmark JSON written to {json_output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MeshChatX Backend Benchmarker")
    parser.add_argument(
        "--extreme",
        action="store_true",
        help="Run extreme stress tests",
    )
    parser.add_argument(
        "--json-output",
        metavar="PATH",
        default=None,
        help="Write benchmark results as github-action-benchmark customSmallerIsBetter JSON to PATH",
    )
    args = parser.parse_args()

    bench = BackendBenchmarker()
    try:
        bench.run_all(extreme=args.extreme, json_output_path=args.json_output)
    finally:
        bench.cleanup()
