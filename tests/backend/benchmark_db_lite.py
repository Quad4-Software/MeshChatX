# SPDX-License-Identifier: 0BSD

import os
import random
import secrets
import shutil
import tempfile
import time

from meshchatx.src.backend.database import Database


def generate_hash():
    return secrets.token_hex(16)


def test_db_performance():
    dir_path = tempfile.mkdtemp()
    db_path = os.path.join(dir_path, "test_perf.db")
    db = Database(db_path)
    db.initialize()

    # Reduced numbers for faster execution in CI/Test environment
    num_peers = 100
    num_messages_per_peer = 100
    total_messages = num_peers * num_messages_per_peer

    peer_hashes = [generate_hash() for _ in range(num_peers)]
    my_hash = generate_hash()

    print(f"Inserting {total_messages} messages for {num_peers} peers...")
    start_time = time.time()

    # Use a transaction for bulk insertion to see potential speedup if we implement it
    # But for now, using the standard DAO method
    for i, peer_hash in enumerate(peer_hashes):
        if i % 25 == 0:
            print(f"Progress: {i}/{num_peers} peers")
        for j in range(num_messages_per_peer):
            is_incoming = random.choice([0, 1])
            src = peer_hash if is_incoming else my_hash
            dst = my_hash if is_incoming else peer_hash

            msg = {
                "hash": generate_hash(),
                "source_hash": src,
                "destination_hash": dst,
                "peer_hash": peer_hash,  # Use peer_hash directly as the app does now
                "state": "delivered",
                "progress": 1.0,
                "is_incoming": is_incoming,
                "method": "direct",
                "delivery_attempts": 1,
                "title": f"Title {j}",
                "content": f"Content {j} for peer {i}",
                "fields": "{}",
                "timestamp": time.time() - random.randint(0, 1000000),
                "rssi": -random.randint(30, 100),
                "snr": random.random() * 10,
                "quality": random.randint(1, 5),
                "is_spam": 0,
            }
            db.messages.upsert_lxmf_message(msg)

    end_time = time.time()
    print(f"Insertion took {end_time - start_time:.2f} seconds")

    # Test get_conversations
    print("Testing get_conversations()...")
    start_time = time.time()
    convs = db.messages.get_conversations()
    end_time = time.time()
    print(
        f"get_conversations() returned {len(convs)} conversations in {end_time - start_time:.4f} seconds",
    )

    # Test get_conversation_messages for a random peer
    target_peer = random.choice(peer_hashes)
    print(f"Testing get_conversation_messages() for peer {target_peer}...")
    start_time = time.time()
    msgs = db.messages.get_conversation_messages(target_peer, limit=50)
    end_time = time.time()
    print(
        f"get_conversation_messages() returned {len(msgs)} messages in {end_time - start_time:.4f} seconds",
    )

    # Test unread states for all peers
    print("Testing get_conversations_unread_states()...")
    start_time = time.time()
    _ = db.messages.get_conversations_unread_states(peer_hashes)
    end_time = time.time()
    print(
        f"get_conversations_unread_states() for {len(peer_hashes)} peers took {end_time - start_time:.4f} seconds",
    )

    # Test announces performance
    num_announces = 5000
    print(f"Inserting {num_announces} announces...")
    start_time = time.time()
    for i in range(num_announces):
        ann = {
            "destination_hash": generate_hash(),
            "aspect": "lxmf.delivery",
            "identity_hash": generate_hash(),
            "identity_public_key": secrets.token_hex(32),
            "app_data": "some app data",
            "rssi": -random.randint(30, 100),
            "snr": random.random() * 10,
            "quality": random.randint(1, 5),
        }
        db.announces.upsert_announce(ann)
    end_time = time.time()
    print(f"Announce insertion took {end_time - start_time:.2f} seconds")

    print("Testing get_filtered_announces()...")
    start_time = time.time()
    _ = db.announces.get_filtered_announces(limit=100)
    end_time = time.time()
    print(f"get_filtered_announces() took {end_time - start_time:.4f} seconds")

    print("Testing trim_announces_for_aspect()...")
    start_time = time.time()
    db.announces.trim_announces_for_aspect("lxmf.delivery", 1000)
    end_time = time.time()
    print(f"trim_announces_for_aspect() took {end_time - start_time:.4f} seconds")

    shutil.rmtree(dir_path)


if __name__ == "__main__":
    test_db_performance()
