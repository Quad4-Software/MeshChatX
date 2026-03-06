"""Performance regression tests for the critical hot paths.

Focus areas (user priority):
  - NomadNet browser: load announces, search announces, favourites
  - Messages: load conversations, search messages, load conversation messages,
              upsert messages (drafts)

Metrics collected:
  - ops/sec throughput
  - p50 / p95 / p99 latency
  - Concurrent writer contention
  - LIKE-search scaling

All tests have hard assertions so regressions fail CI.
"""

import os
import secrets
import shutil
import statistics
import tempfile
import threading
import time
import unittest

from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.message_handler import MessageHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def percentile(data, pct):
    """Return the pct-th percentile of sorted data."""
    if not data:
        return 0
    s = sorted(data)
    k = (len(s) - 1) * (pct / 100)
    f = int(k)
    c = f + 1
    if c >= len(s):
        return s[f]
    return s[f] + (k - f) * (s[c] - s[f])


def timed_call(fn, *args, **kwargs):
    """Call fn and return (result, duration_ms)."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, (time.perf_counter() - t0) * 1000


def latency_report(name, durations_ms):
    """Print and return latency stats."""
    p50 = percentile(durations_ms, 50)
    p95 = percentile(durations_ms, 95)
    p99 = percentile(durations_ms, 99)
    avg = statistics.mean(durations_ms)
    ops = 1000 / avg if avg > 0 else float("inf")
    print(
        f"  {name}: avg={avg:.2f}ms  p50={p50:.2f}ms  p95={p95:.2f}ms  "
        f"p99={p99:.2f}ms  ops/s={ops:.0f}"
    )
    return {"avg": avg, "p50": p50, "p95": p95, "p99": p99, "ops": ops}


def make_message(peer_hash, i, content_size=100):
    return {
        "hash": secrets.token_hex(16),
        "source_hash": peer_hash,
        "destination_hash": "local_hash_0" * 2,
        "peer_hash": peer_hash,
        "state": "delivered",
        "progress": 1.0,
        "is_incoming": i % 2,
        "method": "direct",
        "delivery_attempts": 1,
        "next_delivery_attempt_at": None,
        "title": f"Message title {i} " + secrets.token_hex(8),
        "content": f"Content body {i} " + "x" * content_size,
        "fields": "{}",
        "timestamp": time.time() - i,
        "rssi": -50,
        "snr": 5.0,
        "quality": 3,
        "is_spam": 0,
        "reply_to_hash": None,
    }


def make_announce(i):
    return {
        "destination_hash": secrets.token_hex(16),
        "aspect": "lxmf.delivery" if i % 3 != 0 else "lxst.telephony",
        "identity_hash": secrets.token_hex(16),
        "identity_public_key": "pubkey_" + secrets.token_hex(8),
        "app_data": "appdata_" + secrets.token_hex(16),
        "rssi": -50 + (i % 30),
        "snr": 5.0,
        "quality": i % 10,
    }


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestPerformanceHotPaths(unittest.TestCase):
    NUM_MESSAGES = 10_000
    NUM_PEERS = 200
    NUM_ANNOUNCES = 5_000
    NUM_FAVOURITES = 100
    NUM_CONTACTS = 50

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.test_dir, "perf_hotpaths.db")
        cls.db = Database(cls.db_path)
        cls.db.initialize()
        cls.handler = MessageHandler(cls.db)
        cls.announce_mgr = AnnounceManager(cls.db)

        cls._seed_data()

    @classmethod
    def tearDownClass(cls):
        cls.db.close_all()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    @classmethod
    def _seed_data(cls):
        print("\n--- Seeding test data ---")

        # Peers
        cls.peer_hashes = [secrets.token_hex(16) for _ in range(cls.NUM_PEERS)]
        cls.heavy_peer = cls.peer_hashes[0]

        # Messages: distribute across peers, heavy_peer gets 2000
        print(f"  Seeding {cls.NUM_MESSAGES} messages across {cls.NUM_PEERS} peers...")
        t0 = time.perf_counter()
        with cls.db.provider:
            for i in range(cls.NUM_MESSAGES):
                if i < 2000:
                    peer = cls.heavy_peer
                else:
                    peer = cls.peer_hashes[i % cls.NUM_PEERS]
                cls.db.messages.upsert_lxmf_message(make_message(peer, i))
        print(f"    Done in {(time.perf_counter() - t0) * 1000:.0f}ms")

        # Announces
        print(f"  Seeding {cls.NUM_ANNOUNCES} announces...")
        cls.announce_hashes = []
        t0 = time.perf_counter()
        with cls.db.provider:
            for i in range(cls.NUM_ANNOUNCES):
                data = make_announce(i)
                cls.announce_hashes.append(data["destination_hash"])
                cls.db.announces.upsert_announce(data)
        print(f"    Done in {(time.perf_counter() - t0) * 1000:.0f}ms")

        # Favourites
        print(f"  Seeding {cls.NUM_FAVOURITES} favourites...")
        with cls.db.provider:
            for i in range(cls.NUM_FAVOURITES):
                cls.db.announces.upsert_favourite(
                    cls.announce_hashes[i],
                    f"Fav Node {i}",
                    "lxmf.delivery",
                )

        # Contacts (for JOIN benchmarks)
        print(f"  Seeding {cls.NUM_CONTACTS} contacts...")
        with cls.db.provider:
            for i in range(cls.NUM_CONTACTS):
                cls.db.contacts.add_contact(
                    name=f"Contact {i}",
                    remote_identity_hash=cls.peer_hashes[i % cls.NUM_PEERS],
                    lxmf_address=cls.peer_hashes[(i + 1) % cls.NUM_PEERS],
                )

        print("--- Seeding complete ---\n")

    # ===================================================================
    # ANNOUNCES — load, search, count
    # ===================================================================

    def test_announce_load_filtered_latency(self):
        """Load announces filtered by aspect with pagination — the NomadNet browser default view."""
        print("\n[Announce] Filtered load (aspect + pagination):")
        durations = []
        offsets = [0, 100, 500, 1000, 2000]
        for offset in offsets:
            _, ms = timed_call(
                self.announce_mgr.get_filtered_announces,
                aspect="lxmf.delivery",
                limit=50,
                offset=offset,
            )
            durations.append(ms)

        stats = latency_report("filtered_load", durations)
        self.assertLess(stats["p99"], 100, "Announce filtered load p99 > 100ms")

    def test_announce_search_latency(self):
        """Search announces by destination/identity hash substring."""
        print("\n[Announce] LIKE search:")
        search_terms = [
            secrets.token_hex(4),
            "abc",
            self.announce_hashes[0][:8],
            self.announce_hashes[2500][:10],
            "nonexistent_term_xyz",
        ]
        durations = []
        for term in search_terms:
            _, ms = timed_call(
                self.announce_mgr.get_filtered_announces,
                aspect="lxmf.delivery",
                query=term,
                limit=50,
                offset=0,
            )
            durations.append(ms)

        stats = latency_report("search", durations)
        self.assertLess(stats["p95"], 150, "Announce search p95 > 150ms")

    def test_announce_search_with_blocked(self):
        """Search with a block-list — simulates real NomadNet browser filtering."""
        print("\n[Announce] Search with blocked list:")
        blocked = [secrets.token_hex(16) for _ in range(50)]
        durations = []
        for _ in range(20):
            _, ms = timed_call(
                self.announce_mgr.get_filtered_announces,
                aspect="lxmf.delivery",
                query="abc",
                blocked_identity_hashes=blocked,
                limit=50,
                offset=0,
            )
            durations.append(ms)

        stats = latency_report("search+blocked", durations)
        self.assertLess(stats["p95"], 200, "Announce search+blocked p95 > 200ms")

    def test_announce_count_latency(self):
        """Count announces (used for pagination total)."""
        print("\n[Announce] Count:")
        durations = []
        for _ in range(30):
            _, ms = timed_call(
                self.announce_mgr.get_filtered_announces_count,
                aspect="lxmf.delivery",
            )
            durations.append(ms)

        stats = latency_report("count", durations)
        self.assertLess(stats["p95"], 100, "Announce count p95 > 100ms")

    # ===================================================================
    # FAVOURITES
    # ===================================================================

    def test_favourites_load_latency(self):
        """Load all favourites — typically displayed in sidebar."""
        print("\n[Favourites] Load all:")
        durations = []
        for _ in range(50):
            _, ms = timed_call(self.db.announces.get_favourites, "lxmf.delivery")
            durations.append(ms)

        stats = latency_report("load_favs", durations)
        self.assertLess(stats["p95"], 20, "Favourites load p95 > 20ms")

    def test_favourite_upsert_throughput(self):
        """Measure upsert throughput for favourites."""
        print("\n[Favourites] Upsert throughput:")
        durations = []
        for i in range(100):
            dest = secrets.token_hex(16)
            _, ms = timed_call(
                self.db.announces.upsert_favourite,
                dest,
                f"Bench Fav {i}",
                "lxmf.delivery",
            )
            durations.append(ms)

        stats = latency_report("upsert_fav", durations)
        self.assertGreater(stats["ops"], 500, "Favourite upsert < 500 ops/s")

    # ===================================================================
    # CONVERSATIONS — load, search
    # ===================================================================

    def test_conversations_load_latency(self):
        """Load conversation list — the main messages sidebar query."""
        print("\n[Conversations] Load list (with JOINs):")
        durations = []
        for _ in range(20):
            _, ms = timed_call(
                self.handler.get_conversations,
                "local_hash",
                limit=50,
                offset=0,
            )
            durations.append(ms)

        stats = latency_report("load_conversations", durations)
        self.assertLess(stats["p95"], 200, "Conversation list p95 > 200ms")

    def test_conversations_search_latency(self):
        """Search conversations — LIKE across titles, content, peer hashes."""
        print("\n[Conversations] Search:")
        terms = [
            "Message title 5",
            "Content body",
            "abc",
            "zzz_nope",
            self.heavy_peer[:8],
        ]
        durations = []
        for term in terms:
            _, ms = timed_call(
                self.handler.get_conversations,
                "local_hash",
                search=term,
                limit=50,
            )
            durations.append(ms)

        stats = latency_report("search_conversations", durations)
        self.assertLess(stats["p95"], 500, "Conversation search p95 > 500ms")

    def test_conversations_load_paginated(self):
        """Paginate through conversation list at various offsets."""
        print("\n[Conversations] Paginated load:")
        durations = []
        for offset in [0, 20, 50, 100, 150]:
            _, ms = timed_call(
                self.handler.get_conversations,
                "local_hash",
                limit=20,
                offset=offset,
            )
            durations.append(ms)

        stats = latency_report("paginated_conversations", durations)
        self.assertLess(stats["p95"], 300, "Paginated conversations p95 > 300ms")

    # ===================================================================
    # MESSAGES — load, search, upsert (drafts)
    # ===================================================================

    def test_message_load_latency(self):
        """Load messages for a single conversation (heavy peer with 2000 msgs)."""
        print("\n[Messages] Load conversation messages:")
        durations = []
        offsets = [0, 100, 500, 1000, 1900]
        for offset in offsets:
            result, ms = timed_call(
                self.handler.get_conversation_messages,
                "local_hash",
                self.heavy_peer,
                limit=50,
                offset=offset,
            )
            durations.append(ms)
            self.assertEqual(len(result), 50)

        stats = latency_report("load_messages", durations)
        self.assertLess(stats["p99"], 50, "Message load p99 > 50ms")

    def test_message_search_latency(self):
        """Search messages across all conversations — the global search."""
        print("\n[Messages] Global search:")
        terms = [
            "Message title 100",
            "Content body 5000",
            secrets.token_hex(4),
            "nonexistent_xyz_123",
        ]
        durations = []
        for term in terms:
            _, ms = timed_call(
                self.handler.search_messages,
                "local_hash",
                term,
            )
            durations.append(ms)

        stats = latency_report("search_messages", durations)
        self.assertLess(stats["p95"], 300, "Message search p95 > 300ms")

    def test_message_upsert_throughput(self):
        """Measure message upsert throughput — simulates saving drafts rapidly."""
        print("\n[Messages] Upsert throughput (draft saves):")
        durations = []
        peer = secrets.token_hex(16)
        for i in range(200):
            msg = make_message(peer, i + 100000)
            _, ms = timed_call(self.db.messages.upsert_lxmf_message, msg)
            durations.append(ms)

        stats = latency_report("upsert_message", durations)
        self.assertGreater(stats["ops"], 300, "Message upsert < 300 ops/s")
        self.assertLess(stats["p95"], 10, "Message upsert p95 > 10ms")

    def test_message_upsert_update_throughput(self):
        """Measure message UPDATE throughput — re-saving existing messages (state changes)."""
        print("\n[Messages] Update existing messages:")
        peer = secrets.token_hex(16)
        msgs = []
        for i in range(100):
            msg = make_message(peer, i + 200000)
            self.db.messages.upsert_lxmf_message(msg)
            msgs.append(msg)

        durations = []
        for msg in msgs:
            msg["state"] = "failed"
            msg["content"] = "Updated content " + secrets.token_hex(16)
            _, ms = timed_call(self.db.messages.upsert_lxmf_message, msg)
            durations.append(ms)

        stats = latency_report("update_message", durations)
        self.assertGreater(stats["ops"], 300, "Message update < 300 ops/s")

    # ===================================================================
    # CONCURRENT WRITERS — contention stress
    # ===================================================================

    def test_concurrent_message_writers(self):
        """Multiple threads inserting messages simultaneously."""
        print("\n[Concurrency] Message writers:")
        num_threads = 8
        msgs_per_thread = 100
        errors = []
        all_durations = []
        lock = threading.Lock()

        def writer(thread_id):
            thread_durations = []
            peer = secrets.token_hex(16)
            for i in range(msgs_per_thread):
                msg = make_message(peer, thread_id * 10000 + i)
                try:
                    _, ms = timed_call(self.db.messages.upsert_lxmf_message, msg)
                    thread_durations.append(ms)
                except Exception as e:
                    errors.append(str(e))
            with lock:
                all_durations.extend(thread_durations)

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_threads)
        ]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall_ms = (time.perf_counter() - t0) * 1000

        total_ops = num_threads * msgs_per_thread
        throughput = total_ops / (wall_ms / 1000)
        print(
            f"  Wall time: {wall_ms:.0f}ms for {total_ops} inserts ({throughput:.0f} ops/s)"
        )
        latency_report("concurrent_write", all_durations)

        self.assertEqual(len(errors), 0, f"Writer errors: {errors[:5]}")
        self.assertGreater(throughput, 100, "Concurrent write throughput < 100 ops/s")

    def test_concurrent_announce_writers(self):
        """Multiple threads upserting announces simultaneously."""
        print("\n[Concurrency] Announce writers:")
        num_threads = 6
        announces_per_thread = 100
        errors = []
        all_durations = []
        lock = threading.Lock()

        def writer(thread_id):
            thread_durations = []
            for i in range(announces_per_thread):
                data = make_announce(thread_id * 10000 + i)
                try:
                    _, ms = timed_call(self.db.announces.upsert_announce, data)
                    thread_durations.append(ms)
                except Exception as e:
                    errors.append(str(e))
            with lock:
                all_durations.extend(thread_durations)

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_threads)
        ]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall_ms = (time.perf_counter() - t0) * 1000

        total_ops = num_threads * announces_per_thread
        throughput = total_ops / (wall_ms / 1000)
        print(
            f"  Wall time: {wall_ms:.0f}ms for {total_ops} upserts ({throughput:.0f} ops/s)"
        )
        latency_report("concurrent_announce_write", all_durations)

        self.assertEqual(len(errors), 0, f"Writer errors: {errors[:5]}")
        self.assertGreater(throughput, 100, "Concurrent announce write < 100 ops/s")

    def test_concurrent_read_write_contention(self):
        """Writers inserting while readers query — simulates real app usage."""
        print("\n[Contention] Mixed read/write:")
        num_writers = 4
        num_readers = 4
        ops_per_thread = 50
        write_errors = []
        read_errors = []
        write_durations = []
        read_durations = []
        lock = threading.Lock()

        def writer(thread_id):
            local_durs = []
            peer = secrets.token_hex(16)
            for i in range(ops_per_thread):
                msg = make_message(peer, thread_id * 10000 + i)
                try:
                    _, ms = timed_call(self.db.messages.upsert_lxmf_message, msg)
                    local_durs.append(ms)
                except Exception as e:
                    write_errors.append(str(e))
            with lock:
                write_durations.extend(local_durs)

        def reader(_thread_id):
            local_durs = []
            for _ in range(ops_per_thread):
                try:
                    _, ms = timed_call(
                        self.handler.get_conversations,
                        "local_hash",
                        limit=20,
                    )
                    local_durs.append(ms)
                except Exception as e:
                    read_errors.append(str(e))
            with lock:
                read_durations.extend(local_durs)

        writers = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_writers)
        ]
        readers = [
            threading.Thread(target=reader, args=(t,)) for t in range(num_readers)
        ]

        t0 = time.perf_counter()
        for t in writers + readers:
            t.start()
        for t in writers + readers:
            t.join()
        wall_ms = (time.perf_counter() - t0) * 1000

        print(f"  Wall time: {wall_ms:.0f}ms")
        latency_report("contention_writes", write_durations)
        latency_report("contention_reads", read_durations)

        self.assertEqual(len(write_errors), 0, f"Write errors: {write_errors[:5]}")
        self.assertEqual(len(read_errors), 0, f"Read errors: {read_errors[:5]}")

    # ===================================================================
    # LIKE SEARCH SCALING — how search degrades with data size
    # ===================================================================

    def test_like_search_scaling(self):
        """Measure how LIKE search scales across different table sizes.
        This catches missing FTS indexes or query plan regressions."""
        print("\n[Scaling] LIKE search across data sizes:")

        # Message search on the existing 10k dataset
        _, ms_msg = timed_call(
            self.handler.search_messages,
            "local_hash",
            "Content body",
        )
        print(f"  Message LIKE search ({self.NUM_MESSAGES} rows): {ms_msg:.2f}ms")
        self.assertLess(ms_msg, 500, "Message LIKE search > 500ms on 10k rows")

        # Announce search on the existing 5k dataset
        _, ms_ann = timed_call(
            self.announce_mgr.get_filtered_announces,
            aspect="lxmf.delivery",
            query="abc",
            limit=50,
        )
        print(f"  Announce LIKE search ({self.NUM_ANNOUNCES} rows): {ms_ann:.2f}ms")
        self.assertLess(ms_ann, 200, "Announce LIKE search > 200ms on 5k rows")

        # Contacts search
        _, ms_con = timed_call(self.db.contacts.get_contacts, search="Contact")
        print(f"  Contacts LIKE search ({self.NUM_CONTACTS} rows): {ms_con:.2f}ms")
        self.assertLess(ms_con, 50, "Contacts LIKE search > 50ms")

    # ===================================================================
    # N+1 BATCH OPERATIONS — transaction wrapping regression tests
    # ===================================================================

    def test_mark_conversations_as_read_batch(self):
        """mark_conversations_as_read should be fast for large batches (transaction-wrapped)."""
        print("\n[Batch] mark_conversations_as_read:")
        hashes = [secrets.token_hex(16) for _ in range(200)]
        durations = []
        for _ in range(5):
            _, ms = timed_call(self.db.messages.mark_conversations_as_read, hashes)
            durations.append(ms)

        stats = latency_report("mark_read_200", durations)
        self.assertLess(stats["p95"], 50, "mark_conversations_as_read(200) p95 > 50ms")

    def test_mark_all_notifications_as_viewed_batch(self):
        """mark_all_notifications_as_viewed should be fast for large batches."""
        print("\n[Batch] mark_all_notifications_as_viewed:")
        hashes = [secrets.token_hex(16) for _ in range(200)]
        durations = []
        for _ in range(5):
            _, ms = timed_call(
                self.db.messages.mark_all_notifications_as_viewed, hashes
            )
            durations.append(ms)

        stats = latency_report("mark_viewed_200", durations)
        self.assertLess(
            stats["p95"], 50, "mark_all_notifications_as_viewed(200) p95 > 50ms"
        )

    def test_move_conversations_to_folder_batch(self):
        """move_conversations_to_folder should be fast for large batches."""
        print("\n[Batch] move_conversations_to_folder:")
        self.db.messages.create_folder("perf_test_folder")
        folders = self.db.messages.get_all_folders()
        folder_id = folders[0]["id"]

        hashes = [secrets.token_hex(16) for _ in range(200)]
        durations = []
        for _ in range(5):
            _, ms = timed_call(
                self.db.messages.move_conversations_to_folder, hashes, folder_id
            )
            durations.append(ms)

        stats = latency_report("move_folder_200", durations)
        self.assertLess(
            stats["p95"], 50, "move_conversations_to_folder(200) p95 > 50ms"
        )

    # ===================================================================
    # INDEX VERIFICATION — confirm new indexes are used
    # ===================================================================

    def test_indexes_exist(self):
        """Verify critical indexes exist in the schema."""
        print("\n[Indexes] Checking critical indexes exist:")
        rows = self.db.provider.fetchall(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        index_names = {r["name"] for r in rows}

        expected = [
            "idx_contacts_lxmf_address",
            "idx_contacts_lxst_address",
            "idx_notifications_is_viewed",
            "idx_map_drawings_identity_hash",
            "idx_map_drawings_identity_name",
            "idx_voicemails_is_read",
            "idx_archived_pages_created_at",
            "idx_lxmf_messages_state_peer",
            "idx_lxmf_messages_peer_hash",
            "idx_lxmf_messages_peer_ts",
            "idx_announces_updated_at",
            "idx_announces_aspect",
        ]
        for idx in expected:
            self.assertIn(idx, index_names, f"Missing index: {idx}")
            print(f"  {idx}: OK")

    def test_pragmas_applied(self):
        """Verify performance PRAGMAs are active."""
        print("\n[PRAGMAs] Checking applied PRAGMAs:")
        journal = self.db._get_pragma_value("journal_mode")
        print(f"  journal_mode: {journal}")
        self.assertEqual(journal, "wal")

        sync = self.db._get_pragma_value("synchronous")
        print(f"  synchronous: {sync}")
        self.assertEqual(sync, 1)  # NORMAL = 1

        temp_store = self.db._get_pragma_value("temp_store")
        print(f"  temp_store: {temp_store}")
        self.assertEqual(temp_store, 2)  # MEMORY = 2

        cache_size = self.db._get_pragma_value("cache_size")
        print(f"  cache_size: {cache_size}")
        self.assertLessEqual(cache_size, -8000)

    # ===================================================================
    # QUERY PLAN CHECKS — confirm indexes are actually used
    # ===================================================================

    def test_query_plan_messages_by_peer(self):
        """The most common message query should use peer_hash index."""
        print("\n[Query Plan] Messages by peer_hash:")
        rows = self.db.provider.fetchall(
            "EXPLAIN QUERY PLAN SELECT * FROM lxmf_messages WHERE peer_hash = ? ORDER BY id DESC LIMIT 50",
            ("test",),
        )
        plan = " ".join(str(r["detail"]) for r in rows)
        print(f"  {plan}")
        self.assertIn("idx_lxmf_messages_peer_hash", plan.lower())

    def test_query_plan_announces_by_aspect(self):
        """Announce filtering by aspect should use the aspect index."""
        print("\n[Query Plan] Announces by aspect:")
        rows = self.db.provider.fetchall(
            "EXPLAIN QUERY PLAN SELECT * FROM announces WHERE aspect = ? ORDER BY updated_at DESC LIMIT 50",
            ("lxmf.delivery",),
        )
        plan = " ".join(str(r["detail"]) for r in rows)
        print(f"  {plan}")
        self.assertIn("idx_announces_aspect", plan.lower())

    def test_query_plan_failed_messages_state_peer(self):
        """The failed_count subquery should use the state+peer composite index."""
        print("\n[Query Plan] Failed messages (state, peer_hash):")
        rows = self.db.provider.fetchall(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM lxmf_messages WHERE state = 'failed' AND peer_hash = ?",
            ("test",),
        )
        plan = " ".join(str(r["detail"]) for r in rows)
        print(f"  {plan}")
        self.assertIn("idx_lxmf_messages_state_peer", plan.lower())

    def test_query_plan_notifications_unread(self):
        """Notification unread filter should use the is_viewed index."""
        print("\n[Query Plan] Notifications unread:")
        rows = self.db.provider.fetchall(
            "EXPLAIN QUERY PLAN SELECT * FROM notifications WHERE is_viewed = 0 ORDER BY timestamp DESC LIMIT 50",
        )
        plan = " ".join(str(r["detail"]) for r in rows)
        print(f"  {plan}")
        self.assertIn("idx_notifications_is_viewed", plan.lower())


if __name__ == "__main__":
    unittest.main()
