# SPDX-License-Identifier: 0BSD

"""Tests for the opt-in peer update relay server.

The server only serves manifests it verified itself and artifacts whose
sha256 appears in a verified manifest. Peers are untrusted transports.
"""

import hashlib
import time

import pytest
import RNS

_REAL_IDENTITY = RNS.Identity

from meshchatx.src.backend import update_peer as up
from meshchatx.src.update_rsm import sign_manifest
from tests.backend.test_update_transports import _manifest


def _pack(obj):
    return up._mp_pack(obj)


def _unpack(data):
    return up._mp_unpack(data)


@pytest.fixture
def server(tmp_path):
    signer = _REAL_IDENTITY()
    payload = b"peer-artifact-bytes" * 100
    name = "pkg-9.9.9.whl"
    p = tmp_path / name
    p.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    manifest = _manifest(
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": sha,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ]
    )
    rsm = sign_manifest(manifest, signer)
    srv = up.PeerUpdateServer()
    srv.register_manifest("stable", rsm, manifest)
    srv.register_artifact(name, p, sha, len(payload))
    srv.enabled = True
    return srv, name, payload, rsm


def test_probe_same_and_ok(server):
    srv, _name, _payload, rsm = server
    sha = hashlib.sha256(rsm).hexdigest()
    # unknown sha -> full manifest offered
    resp = _unpack(
        srv._handle(_pack({"op": "probe", "channel": "stable", "sha256": "00" * 32}))
    )
    assert resp["s"] == "ok" and resp["d"] == rsm
    # known sha -> tiny "same" reply, no manifest bytes
    resp = _unpack(
        srv._handle(_pack({"op": "probe", "channel": "stable", "sha256": sha}))
    )
    assert resp["s"] == "same"
    # unknown channel -> none
    resp = _unpack(srv._handle(_pack({"op": "probe", "channel": "beta", "sha256": ""})))
    assert resp["s"] == "none"


def test_manifest_op(server):
    srv, _name, _payload, rsm = server
    resp = _unpack(srv._handle(_pack({"op": "manifest", "channel": "stable"})))
    assert resp["s"] == "ok" and resp["d"] == rsm


def test_head_and_range(server):
    srv, name, payload, _rsm = server
    resp = _unpack(srv._handle(_pack({"op": "head", "name": name})))
    assert resp["s"] == "ok" and resp["size"] == len(payload)
    resp = _unpack(srv._handle(_pack({"op": "range", "name": name, "o": 10, "l": 100})))
    assert resp["s"] == "ok" and resp["d"] == payload[10:110]
    # out-of-range clamps
    resp = _unpack(
        srv._handle(
            _pack({"op": "range", "name": name, "o": len(payload) - 5, "l": 100})
        )
    )
    assert resp["d"] == payload[-5:]


def test_refuses_unverified_artifact(tmp_path):
    """Unverified artifacts are never served.

    Even when registered, an artifact whose sha256 is not in any verified
    manifest must not be served.
    """
    srv = up.PeerUpdateServer()
    srv.enabled = True
    rogue = tmp_path / "rogue.bin"
    rogue.write_bytes(b"not in any manifest")
    srv.register_artifact(
        "rogue.bin",
        rogue,
        hashlib.sha256(b"not in any manifest").hexdigest(),
        rogue.stat().st_size,
    )
    resp = _unpack(srv._handle(_pack({"op": "head", "name": "rogue.bin"})))
    assert resp["s"] == "none"
    resp = _unpack(
        srv._handle(_pack({"op": "range", "name": "rogue.bin", "o": 0, "l": 10}))
    )
    assert resp["s"] == "none"


def test_bad_requests_return_none(server):
    srv, *_rest = server
    for req in [
        b"not msgpack",
        _pack([1, 2, 3]),
        _pack({"op": "bogus"}),
        _pack({"op": "range", "name": "x", "o": "nan", "l": 1}),
        _pack({"op": "range", "name": "../evil", "o": 0, "l": 1}),
        _pack(
            {
                "op": "range",
                "name": "pkg-9.9.9.whl",
                "o": 0,
                "l": up.RNS_RANGE_MAX_BYTES + 1,
            }
        ),
    ]:
        resp = _unpack(srv._handle(req))
        assert resp["s"] == "none", req


def test_disabled_server_answers_none(server):
    srv, *_rest = server
    srv.enabled = False
    resp = srv._responder(
        "/update", _pack({"op": "probe"}), "rid", "lid", "id", time.time()
    )
    assert resp is None


def test_rate_limit(server):
    srv, *_rest = server
    srv._rate = 0.001
    srv._burst = 2.0
    # drain the bucket
    for _ in range(3):
        srv._bucket_for("peer1").allow(1.0)
    # now requests from that peer are refused
    resp = _unpack(
        srv._responder(
            "/update",
            _pack({"op": "probe", "channel": "stable"}),
            "rid",
            "lid",
            "peer1",
            time.time(),
        )
    )
    assert resp == {"s": "none"}


def test_scan_seed_dir_only_verified(tmp_path):
    signer = _REAL_IDENTITY()
    good = b"good-artifact"
    bad = b"unverified-artifact"
    name = "pkg-9.9.9.whl"
    gp = tmp_path / "seeds" / name
    gp.parent.mkdir(parents=True)
    gp.write_bytes(good)
    (tmp_path / "seeds" / "evil.whl").write_bytes(bad)
    manifest = _manifest(
        artifacts=[
            {
                "name": name,
                "size": len(good),
                "sha256": hashlib.sha256(good).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ]
    )
    rsm = sign_manifest(manifest, signer)
    srv = up.PeerUpdateServer()
    srv.register_manifest("stable", rsm, manifest)
    n = srv.scan_seed_dir(tmp_path / "seeds")
    assert n == 1
    assert name in srv._artifacts
    assert "evil.whl" not in srv._artifacts
