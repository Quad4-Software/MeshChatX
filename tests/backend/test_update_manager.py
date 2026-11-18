# SPDX-License-Identifier: 0BSD

"""End-to-end tests for the opt-in update manager.

Covers: defaults off (no transport touched), signed check over a local
http.server, download+stage, block reuse byte savings, downgrade and
high-water replay protection, expiry, channel binding, oversize caps,
sha256 mismatch retry, offline apply-file, settings validation, peer
relay gating, and atomic pending marker contents.
"""

import hashlib
import json
import os
import time

import pytest
import RNS

_REAL_IDENTITY = RNS.Identity

from meshchatx.src.backend import update_types as T
from meshchatx.src.backend.update_blockmap import build_blockmap, encode_blockmap
from meshchatx.src.backend.update_manager import UpdateManager
from meshchatx.src.backend.update_types import (
    UpdateError,
    UpdateUnavailable,
    UpdateVerifyError,
)
from meshchatx.src.update_rsm import sign_manifest
from tests.backend.test_update_transports import _RangeHandler


@pytest.fixture
def http_server():
    """Local HTTP file server with ETag/304 and Range support."""
    import threading
    from http.server import ThreadingHTTPServer

    from tests.backend.test_update_transports import (
        _RangeHandler as _H,
    )

    _H.files = {}
    _H.etags = {}
    _H.requests = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------


class FakeConfig:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = (
            value if not isinstance(value, bool) else ("true" if value else "false")
        )


@pytest.fixture
def signer():
    return _REAL_IDENTITY()


def _manifest(
    version="99.0.0", channel="stable", artifacts=None, issued_at=None, valid_until=None
):
    now = time.time()
    return {
        "schema": 2,
        "app": "reticulum-meshchatx",
        "channel": channel,
        "version": version,
        "issued_at": issued_at if issued_at is not None else now - 60,
        "valid_until": valid_until if valid_until is not None else now + 86400,
        "min_supported_version": "0.0.1",
        "artifacts": artifacts
        if artifacts is not None
        else [
            {
                "name": "meshchatx-99.0.0-py3-none-any.whl",
                "size": 10,
                "sha256": "00" * 32,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    }


def _make_manager(tmp_path, cfg_values, signer, **kw):
    cfg = FakeConfig(cfg_values)
    return UpdateManager(
        tmp_path / "storage",
        config_getter=lambda: cfg,
        build_meta={"build_channel": "stable"},
        **kw,
    ), cfg


def _enabled_config(base_url, signer, **extra):
    values = {
        "updates_enabled": "true",
        "update_channel": "stable",
        "update_transport": "clearnet",
        "update_signer_hashes": json.dumps([signer.hash.hex()]),
        "update_custom_mirrors": json.dumps([base_url]),
    }
    values.update(extra)
    return values


def _serve(files):
    _RangeHandler.files = dict(files)
    _RangeHandler.etags = {}
    if "/updates/stable/manifest.rsm" in files:
        _RangeHandler.etags["/updates/stable/manifest.rsm"] = '"m-etag"'


VER = "99.0.0"


# ---------------------------------------------------------------------------
# defaults / opt-in
# ---------------------------------------------------------------------------


def test_disabled_by_default_touches_nothing(tmp_path, signer):
    mgr, _cfg = _make_manager(tmp_path, {}, signer)
    res = mgr.check_now()
    assert res["status"] == "disabled"
    assert mgr._transports is None  # transports never built
    mgr.start()  # must not start scheduler or peer
    assert mgr._scheduler is None
    assert mgr._peer is None
    st = mgr.status()
    assert st["enabled"] is False
    assert st["settings"]["enabled"] is False


def test_env_disable_overrides_enabled(tmp_path, signer, monkeypatch):
    monkeypatch.setenv("MESHCHATX_UPDATE_DISABLED", "1")
    mgr, _cfg = _make_manager(tmp_path, {"updates_enabled": "true"}, signer)
    assert mgr.check_now()["status"] == "disabled"
    assert mgr.status()["enabled"] is False
    assert mgr.status()["disabled_by_env"] is True


def test_enabled_check_update_available_and_stage(tmp_path, http_server, signer):
    name = "meshchatx-99.0.0-py3-none-any.whl"
    payload = b"PK\x03\x04" + os.urandom(4096)
    sha = hashlib.sha256(payload).hexdigest()
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": sha,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    rsm = sign_manifest(manifest, signer)
    _serve(
        {
            "/updates/stable/manifest.rsm": rsm,
            f"/updates/stable/{VER}/{name}": payload,
        }
    )
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)

    res = mgr.check_now()
    assert res["status"] == "update_available"
    assert res["update"]["version"] == VER
    assert res["update"]["artifact"]["name"] == name

    dl = mgr.download(res["update"]["artifact"])
    assert dl["status"] == "staged"
    assert dl["sha256"] == sha
    pending = mgr.get_pending()["pending"]
    assert pending is not None
    assert pending["file"] == name
    assert pending["sha256"] == sha
    assert pending["kind"] == "wheel"
    assert pending["apply_policy"] == "manual"
    staged = T.pending_dir(mgr.storage_dir) / name
    assert staged.is_file()
    assert staged.read_bytes() == payload

    # second check: ETag 304 -> up_to_date
    res2 = mgr.check_now()
    assert res2["status"] == "up_to_date"


def test_high_water_rejects_older_manifest(tmp_path, http_server, signer):
    name = "pkg.whl"
    payload = b"data"
    sha = hashlib.sha256(payload).hexdigest()
    now = time.time()
    m1 = _manifest(
        version="99.0.0",
        issued_at=now - 100,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": sha,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    m2 = _manifest(
        version="98.0.0",
        issued_at=now - 200,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": sha,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    rsm1 = sign_manifest(m1, signer)
    rsm2 = sign_manifest(m2, signer)
    _serve({"/updates/stable/manifest.rsm": rsm1})
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    assert mgr.check_now()["status"] == "update_available"
    # swap in the older manifest
    _RangeHandler.files["/updates/stable/manifest.rsm"] = rsm2
    _RangeHandler.etags.clear()
    res = mgr.check_now()
    assert res["status"] == "error"
    assert "high-water" in (res.get("error") or "")


def test_downgrade_is_up_to_date(tmp_path, http_server, signer):
    name = "pkg.whl"
    payload = b"data"
    manifest = _manifest(
        version="1.0.0",
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    _serve({"/updates/stable/manifest.rsm": sign_manifest(manifest, signer)})
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    assert res["status"] == "up_to_date"


def test_expired_manifest_rejected(tmp_path, http_server, signer):
    now = time.time()
    manifest = _manifest(version=VER, issued_at=now - 100000, valid_until=now - 1000)
    _serve({"/updates/stable/manifest.rsm": sign_manifest(manifest, signer)})
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    assert res["status"] == "error"


def test_wrong_channel_rejected(tmp_path, http_server, signer):
    manifest = _manifest(version=VER, channel="beta")
    _serve({"/updates/stable/manifest.rsm": sign_manifest(manifest, signer)})
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    assert res["status"] == "error"


def test_wrong_signer_rejected(tmp_path, http_server, signer):
    other = _REAL_IDENTITY()
    manifest = _manifest(version=VER)
    _serve({"/updates/stable/manifest.rsm": sign_manifest(manifest, other)})
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    assert res["status"] == "error"
    assert "signer" in (res.get("error") or "")


def test_tampered_manifest_rejected(tmp_path, http_server, signer):
    manifest = _manifest(version=VER)
    rsm = bytearray(sign_manifest(manifest, signer))
    rsm[-10] ^= 0xFF
    _serve({"/updates/stable/manifest.rsm": bytes(rsm)})
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    assert res["status"] == "error"


def test_oversize_artifact_cap(tmp_path, http_server, signer):
    name = "big.whl"
    payload = b"x" * (2 * 1024 * 1024)
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    _serve({"/updates/stable/manifest.rsm": sign_manifest(manifest, signer)})
    mgr, _cfg = _make_manager(
        tmp_path,
        _enabled_config(http_server, signer, update_max_download_mb="1"),
        signer,
    )
    res = mgr.check_now()
    assert res["status"] == "too_large"


def test_sha_mismatch_download_fails(tmp_path, http_server, signer):
    name = "pkg.whl"
    good = b"correct-bytes"
    bad = b"corrupted-bytes!"
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(good),
                "sha256": hashlib.sha256(good).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    _serve(
        {
            "/updates/stable/manifest.rsm": sign_manifest(manifest, signer),
            f"/updates/stable/{VER}/{name}": bad,
        }
    )
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    assert res["status"] == "update_available"
    with pytest.raises(UpdateVerifyError):
        mgr.download(res["update"]["artifact"])
    # nothing staged
    assert mgr.get_pending()["pending"] is None


# ---------------------------------------------------------------------------
# block reuse
# ---------------------------------------------------------------------------


def test_block_reuse_saves_bytes(tmp_path, http_server, signer, monkeypatch):
    """Block reuse must fetch far fewer bytes than a full download.

    The old installed artifact shares most blocks with the new one.
    """
    BS = 64 * 1024

    # build deterministic pseudo-random blocks
    def blk(i, salt=b""):
        return hashlib.sha256(f"{i}".encode() + salt).digest() * (BS // 32)

    nblocks = 5
    new_data = b"".join(blk(i) for i in range(nblocks))
    # old file: same except block 2 differs
    old_data = b"".join(blk(i) if i != 2 else blk(99) for i in range(nblocks))
    old_path = tmp_path / "old.AppImage"
    old_path.write_bytes(old_data)
    monkeypatch.setenv("APPIMAGE", str(old_path))

    new_path = tmp_path / "new.bin"
    new_path.write_bytes(new_data)
    bm = build_blockmap(new_path, block_size=BS)
    bm_bytes = encode_blockmap(bm)

    name = "MeshChatX-99.0.0.AppImage"
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(new_data),
                "sha256": hashlib.sha256(new_data).hexdigest(),
                "kind": "appimage",
                "platform": "linux",
                "arch": "x86_64",
                "blockmap_sha256": hashlib.sha256(bm_bytes).hexdigest(),
                "block_size": BS,
                "block_count": len(bm["blocks"]),
            }
        ],
    )
    _serve(
        {
            "/updates/stable/manifest.rsm": sign_manifest(manifest, signer),
            f"/updates/stable/{VER}/{name}": new_data,
            f"/updates/stable/{VER}/{name}.blockmap": bm_bytes,
        }
    )
    mgr, _cfg = _make_manager(
        tmp_path,
        _enabled_config(http_server, signer),
        signer,
    )
    res = mgr.check_now()
    assert res["status"] == "update_available", res
    dl = mgr.download(res["update"]["artifact"])
    assert dl["status"] == "staged"
    assert dl["bytes_reused"] > 0
    # only the changed block (plus slack) fetched, far less than full size
    assert dl["bytes_fetched"] < len(new_data)
    assert dl["bytes_fetched"] <= BS * 2
    staged = T.pending_dir(mgr.storage_dir) / name
    assert staged.read_bytes() == new_data


def test_blockmap_tamper_falls_back_to_full(tmp_path, http_server, signer, monkeypatch):
    monkeypatch.delenv("APPIMAGE", raising=False)
    BS = 64 * 1024

    def blk(i):
        return hashlib.sha256(f"x{i}".encode()).digest() * (BS // 32)

    new_data = b"".join(blk(i) for i in range(4))
    new_path = tmp_path / "new.bin"
    new_path.write_bytes(new_data)
    bm = build_blockmap(new_path, block_size=BS)
    bm_bytes = bytearray(encode_blockmap(bm))
    bm_bytes[-3] ^= 0xFF  # corrupt
    name = "pkg.AppImage"
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(new_data),
                "sha256": hashlib.sha256(new_data).hexdigest(),
                "kind": "appimage",
                "platform": "linux",
                "arch": "x86_64",
                "blockmap_sha256": hashlib.sha256(bytes(bm_bytes)).hexdigest(),
                "block_size": BS,
                "block_count": len(bm["blocks"]),
            }
        ],
    )
    _serve(
        {
            "/updates/stable/manifest.rsm": sign_manifest(manifest, signer),
            f"/updates/stable/{VER}/{name}": new_data,
            f"/updates/stable/{VER}/{name}.blockmap": bytes(bm_bytes),
        }
    )
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    dl = mgr.download(res["update"]["artifact"])
    assert dl["status"] == "staged"
    assert dl["bytes_fetched"] == len(new_data)  # full download fallback


# ---------------------------------------------------------------------------
# offline apply-file
# ---------------------------------------------------------------------------


def test_apply_file_offline_with_sidecar_manifest(tmp_path, signer):
    name = "meshchatx-99.0.0-py3-none-any.whl"
    payload = b"wheel-bytes"
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    rsm = sign_manifest(manifest, signer)
    cfg = FakeConfig(
        {
            "update_channel": "stable",
            "update_transport": "clearnet",
            "update_signer_hashes": json.dumps([signer.hash.hex()]),
        }
    )
    mgr = UpdateManager(
        tmp_path / "storage",
        config_getter=lambda: cfg,
        build_meta={"build_channel": "stable"},
    )
    f = tmp_path / name
    f.write_bytes(payload)
    f.with_name(name + ".manifest.rsm").write_bytes(rsm)
    res = mgr.apply_file(str(f))
    assert res["status"] == "staged"
    assert mgr.get_pending()["pending"]["sha256"] == hashlib.sha256(payload).hexdigest()


def test_apply_file_rejects_mismatch(tmp_path, signer):
    name = "pkg.whl"
    payload = b"real"
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(b"other").hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    rsm = sign_manifest(manifest, signer)
    cfg = FakeConfig(
        {
            "update_signer_hashes": json.dumps([signer.hash.hex()]),
        }
    )
    mgr = UpdateManager(
        tmp_path / "storage",
        config_getter=lambda: cfg,
        build_meta={"build_channel": "stable"},
    )
    f = tmp_path / name
    f.write_bytes(payload)
    f.with_name(name + ".manifest.rsm").write_bytes(rsm)
    with pytest.raises(UpdateVerifyError):
        mgr.apply_file(str(f))


def test_apply_file_no_manifest_unavailable(tmp_path):
    cfg = FakeConfig({})
    mgr = UpdateManager(tmp_path / "storage", config_getter=lambda: cfg)
    f = tmp_path / "random.bin"
    f.write_bytes(b"x")
    with pytest.raises(UpdateUnavailable):
        mgr.apply_file(str(f))


# ---------------------------------------------------------------------------
# settings / discard / peer relay gating
# ---------------------------------------------------------------------------


def test_update_settings_persists_and_validates(tmp_path, signer):
    mgr, cfg = _make_manager(tmp_path, {}, signer)
    status = mgr.update_settings(
        {
            "enabled": True,
            "channel": "beta",
            "check_interval_hours": 12,
            "peer_relay": False,
        }
    )
    assert cfg.values["updates_enabled"] == "true"
    assert cfg.values["update_channel"] == "beta"
    assert status["settings"]["enabled"] is True
    assert status["settings"]["channel"] == "beta"
    with pytest.raises(UpdateError):
        mgr.update_settings({"channel": "bogus"})
    with pytest.raises(UpdateError):
        mgr.update_settings({"signer_hashes": ["bad"]})


def test_peer_relay_off_by_default_and_gated(tmp_path, signer, monkeypatch):
    import meshchatx.src.backend.update_manager as umod

    started = []

    class FakePeer:
        enabled = False

        def start(self, identity=None):
            self.enabled = True
            started.append(self)

        def stop(self):
            self.enabled = False

        def register_manifest(self, *a, **k):
            pass

        def register_artifact(self, *a, **k):
            pass

        def scan_seed_dir(self, *a, **k):
            return 0

    monkeypatch.setattr(umod, "PeerUpdateServer", FakePeer)
    # disabled settings: peer never constructed
    mgr, _cfg = _make_manager(tmp_path, {}, signer)
    mgr.start()
    assert mgr._peer is None
    assert started == []
    mgr.stop()
    # enabled + peer_relay: peer constructed once
    mgr2, _cfg2 = _make_manager(
        tmp_path / "b", {"updates_enabled": "true", "update_peer_relay": "true"}, signer
    )
    mgr2.start()
    assert mgr2._peer is not None
    assert len(started) == 1
    mgr2.stop()
    assert mgr2._peer is None


def test_discard_clears_pending(tmp_path, http_server, signer):
    name = "pkg.whl"
    payload = b"data"
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    _serve(
        {
            "/updates/stable/manifest.rsm": sign_manifest(manifest, signer),
            f"/updates/stable/{VER}/{name}": payload,
        }
    )
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    mgr.download(res["update"]["artifact"])
    assert mgr.get_pending()["pending"] is not None
    mgr.discard()
    assert mgr.get_pending()["pending"] is None
    assert not (T.pending_dir(mgr.storage_dir) / name).exists()


def test_status_disclosure_lists_contacts(tmp_path, signer):
    mgr, _cfg = _make_manager(tmp_path, {}, signer)
    st = mgr.status()
    disc = st["disclosure"]
    assert disc["rns_destination"] == T.RNS_UPDATE_ASPECT
    assert len(disc["mirrors"]) >= 1
    assert disc["signer_hashes"]


def test_resume_via_range_after_partial(tmp_path, http_server, signer):
    """A kept .part file resumes with a Range request for the remainder."""
    name = "meshchatx-99.0.0-py3-none-any.whl"
    payload = os.urandom(300 * 1024)
    sha = hashlib.sha256(payload).hexdigest()
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": sha,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    )
    rsm = sign_manifest(manifest, signer)
    _serve(
        {
            "/updates/stable/manifest.rsm": rsm,
            f"/updates/stable/{VER}/{name}": payload,
        }
    )
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)

    # pre-seed the sha-suffixed partial with the first half
    pend = T.pending_dir(mgr.storage_dir)
    pend.mkdir(parents=True, exist_ok=True)
    part = pend / (name + "." + sha[:12] + ".part")
    half = len(payload) // 2
    part.write_bytes(payload[:half])

    res = mgr.check_now()
    assert res["status"] == "update_available"
    dl = mgr.download(res["update"]["artifact"])
    assert dl["status"] == "staged"
    staged = pend / name
    assert staged.read_bytes() == payload
    # the server must have seen a Range request starting at the midpoint
    ranges = [r for r in _RangeHandler.requests if r[1]]
    assert ranges, "expected at least one Range request"
    assert any(r[1].startswith(f"bytes={half}-") for r in ranges)


def test_missing_blockmap_uses_full_download(tmp_path, http_server, signer):
    """Artifact without blockmap metadata downloads whole, no reuse."""
    name = "meshchatx-99.0.0-py3-none-any.whl"
    payload = os.urandom(128 * 1024)
    sha = hashlib.sha256(payload).hexdigest()
    manifest = _manifest(
        version=VER,
        artifacts=[
            {
                "name": name,
                "size": len(payload),
                "sha256": sha,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
                # no blockmap_sha256: reuse path skipped entirely
            }
        ],
    )
    rsm = sign_manifest(manifest, signer)
    _serve(
        {
            "/updates/stable/manifest.rsm": rsm,
            f"/updates/stable/{VER}/{name}": payload,
        }
    )
    mgr, _cfg = _make_manager(tmp_path, _enabled_config(http_server, signer), signer)
    res = mgr.check_now()
    dl = mgr.download(res["update"]["artifact"])
    assert dl["status"] == "staged"
    pending = mgr.get_pending()["pending"]
    assert pending["artifacts"][0]["bytes_fetched"] == len(payload)
    assert pending["artifacts"][0]["bytes_reused"] == 0


# ---------------------------------------------------------------------------
# install kind / artifact pick
# ---------------------------------------------------------------------------


def test_pick_artifact_prefers_install_kind(tmp_path, signer, monkeypatch):
    import meshchatx.src.backend.update_manager as umod

    mgr, _cfg = _make_manager(tmp_path, {}, signer)
    arts = [
        {"name": "a.AppImage", "kind": "appimage"},
        {"name": "a.whl", "kind": "wheel"},
        {"name": "image-ref", "kind": "oci"},
        {"name": "a.flatpak", "kind": "flatpak"},
    ]
    monkeypatch.setattr(umod, "install_kind", lambda: "oci")
    assert mgr._pick_artifact(arts)["kind"] == "oci"
    monkeypatch.setattr(umod, "install_kind", lambda: "flatpak")
    assert mgr._pick_artifact(arts)["kind"] == "flatpak"
    monkeypatch.setattr(umod, "install_kind", lambda: "appimage")
    assert mgr._pick_artifact(arts)["kind"] == "appimage"
    # a plain python install takes the wheel, not the appimage
    monkeypatch.setattr(umod, "install_kind", lambda: "python")
    monkeypatch.setattr(umod, "host_platform", lambda: "linux")
    assert mgr._pick_artifact(arts)["kind"] == "wheel"


def test_pick_artifact_falls_back_to_platform_pref(tmp_path, signer, monkeypatch):
    import meshchatx.src.backend.update_manager as umod

    mgr, _cfg = _make_manager(tmp_path, {}, signer)
    monkeypatch.setattr(umod, "install_kind", lambda: "oci")
    monkeypatch.setattr(umod, "host_platform", lambda: "linux")
    arts = [
        {"name": "a.AppImage", "kind": "appimage"},
        {"name": "a.whl", "kind": "wheel"},
    ]
    assert mgr._pick_artifact(arts)["kind"] == "appimage"


def test_download_refuses_non_file_kinds(tmp_path, signer):
    mgr, _cfg = _make_manager(tmp_path, {"updates_enabled": "true"}, signer)
    res = mgr.download({"kind": "oci", "name": "meshchatx:99.0.0"})
    assert res["status"] == "external"
    assert "container runtime" in res["detail"]
    res = mgr.download({"kind": "flatpak", "name": "pkg.flatpak"})
    assert res["status"] == "external"
    assert "flatpak update" in res["detail"]
    # nothing fetched or staged, transports never built
    assert mgr._transports is None
    assert mgr.get_pending()["pending"] is None
