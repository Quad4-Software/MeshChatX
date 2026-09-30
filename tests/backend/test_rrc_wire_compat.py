# SPDX-License-Identifier: 0BSD
"""Golden wire-format corpus.

The .bin files in wire_corpus/ are canonical CBOR envelopes captured
from the encoder. Decoding them pins the on-the-wire format: a change
to envelope fields, key IDs, or CBOR ordering that would break older
clients fails here before it ships.
"""

from __future__ import annotations

import os
from glob import glob

import pytest

from meshchatx.src.backend.rrc import protocol as proto

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "wire_corpus")

EXPECTED_TYPES = {
    "hello": proto.T_HELLO,
    "welcome": proto.T_WELCOME,
    "joined": proto.T_JOINED,
    "join": proto.T_JOIN,
    "part": proto.T_PART,
    "msg": proto.T_MSG,
    "msg_big": proto.T_MSG,
    "notice": proto.T_NOTICE,
    "error": proto.T_ERROR,
    "pong": proto.T_PONG,
}


def _cases():
    for path in sorted(glob(os.path.join(CORPUS_DIR, "*.bin"))):
        yield pytest.param(path, id=os.path.basename(path))


@pytest.mark.parametrize("path", list(_cases()))
def test_golden_envelope_decodes(path):
    name = os.path.basename(path)[:-4]
    with open(path, "rb") as f:
        data = f.read()
    env = proto.decode(data)
    assert isinstance(env, dict)
    assert env.get(proto.K_V) == proto.RRC_VERSION
    assert env.get(proto.K_T) == EXPECTED_TYPES[name]
    assert isinstance(env.get(proto.K_SRC), (bytes, bytearray))
    assert len(env[proto.K_SRC]) == 16
    # Re-encode must round-trip: the canonical encoding of what we
    # decode equals the captured bytes exactly.
    assert proto.encode(env) == data


def test_corpus_covers_all_pairs():
    files = {os.path.basename(p)[:-4] for p in glob(os.path.join(CORPUS_DIR, "*.bin"))}
    assert files == set(EXPECTED_TYPES), "corpus and expectations drifted"
