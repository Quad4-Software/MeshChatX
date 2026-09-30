# SPDX-License-Identifier: 0BSD
"""Deterministic replay of recorded RRC sessions.

The server can record every routed envelope as JSONL (replay_log on
RRCHubServer). Replaying a capture file through _route exercises the
full session state machine without a live mesh: joins, messages, parts,
errors, and malformed entries all land exactly as they did live.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from test_rrc_server import (
    FakeIdentity,
    FakeLink,
    add_session,
    make_server,
)

from meshchatx.src.backend.rrc import protocol as proto

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "replay_corpus")


def _replay(server, link, sess, rows):
    out = []
    for row in rows:
        env = proto.make_envelope(
            row["t"],
            src=bytes.fromhex(row["src"]) if row.get("src") else sess.peer,
            room=row.get("room"),
            body=row.get("body"),
        )
        server._route(link, sess, env, out)
    return out


def _load(corpus):
    path = os.path.join(CORPUS_DIR, corpus)
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_replay_join_message_part():
    server = make_server()
    link = FakeLink(FakeIdentity(b"peer-replay0000001"))
    sess = add_session(server, link, link._identity.hash, nick="alice")
    rows = _load("join_msg_part.jsonl")
    _replay(server, link, sess, rows)
    # The session joined lobby, then parted: final state is empty
    # membership for the link both in the session and room rosters.
    assert "lobby" not in sess.rooms
    members = server._room_members.get("lobby") or set()
    assert link not in members


def test_replay_malformed_sequence_no_crash():
    server = make_server()
    link = FakeLink(FakeIdentity(b"peer-badseq00001"))
    sess = add_session(server, link, link._identity.hash, nick="mal")
    rows = _load("malformed.jsonl")
    _replay(server, link, sess, rows)  # must not raise
    # Malformed entries must not have joined anything.
    assert not any(sess.rooms)


def test_recording_produces_replayable_jsonl(tmp_path):
    server = make_server()
    server.replay_log = str(tmp_path / "replay.jsonl")
    link = FakeLink(FakeIdentity(b"peer-record00001"))
    sess = add_session(server, link, link._identity.hash, nick="rec")
    env = proto.make_envelope(proto.T_JOIN, src=sess.peer, room="lobby")
    server._record_replay(env)
    with open(server.replay_log) as f:
        row = json.loads(f.readline())
    assert row["t"] == proto.T_JOIN
    assert row["room"] == "lobby"
    # The recorded row replays into an identical server.
    _replay(make_server(), link, sess, [row])
