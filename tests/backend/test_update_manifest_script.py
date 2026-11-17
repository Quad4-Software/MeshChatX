# SPDX-License-Identifier: 0BSD

"""Tests for scripts/build/update_manifest.py.

Covers classification, manifest building, blockmap output and the
sign/verify CLI.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "build" / "update_manifest.py"
)
_spec = importlib.util.spec_from_file_location("update_manifest", _SCRIPT)
um = importlib.util.module_from_spec(_spec)
sys.modules["update_manifest"] = um
_spec.loader.exec_module(um)


def _args(tmp_path, **kw):
    base = {
        "assets": str(tmp_path),
        "version": "1.0.0",
        "channel": "stable",
        "tag": None,
        "min_supported": None,
        "issued_at": None,
        "valid_days": 30,
        "block_size": 64 * 1024,
        "identity": None,
        "out": str(tmp_path / "out"),
    }
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("MeshChatX-1.0.0-linux-x64.AppImage", ("appimage", "linux", "x86_64")),
        ("meshchatx-1.0.0-py3-none-any.whl", ("wheel", "python", "any")),
        ("MeshChatX-1.0.0-arm64.dmg", ("dmg", "macos", "aarch64")),
        ("MeshChatX-1.0.0-win-x64.exe", ("exe", "windows", "x86_64")),
        ("meshchatx-1.0.0.apk", ("apk", "android", "any")),
        ("meshchatx-1.0.0-armv7.deb", ("deb", "linux", "armv7")),
        ("update.rsm", None),
        ("update.json", None),
        ("latest.json", None),
        ("checksums.txt", None),
        ("sbom.cyclonedx.json", None),
        ("file.cosign.bundle", None),
        ("pkg.whl.blockmap", None),
        ("random.xyz", None),
    ],
)
def test_classify_artifact(name, expected):
    res = um.classify_artifact(name)
    if expected is None:
        assert res is None
    else:
        kind, plat, arch = expected
        assert (res["kind"], res["platform"], res["arch"]) == (kind, plat, arch)


def test_build_manifest_collects(tmp_path):
    (tmp_path / "app-1.0.0.AppImage").write_bytes(b"payload")
    (tmp_path / "notes.txt").write_text("skip me")
    m = um.build_manifest(_args(tmp_path, assets=str(tmp_path)))
    assert m["schema"] == 2
    assert m["app"] == "reticulum-meshchatx"
    assert m["channel"] == "stable"
    assert m["version"] == "1.0.0"
    assert len(m["artifacts"]) == 1
    art = m["artifacts"][0]
    assert art["sha256"]
    assert art["size"] == 7
    assert art["blockmap_sha256"]
    assert art["block_size"] == 64 * 1024
    assert art["block_count"] == 1


def test_cli_rejects_bad_channel(tmp_path):
    (tmp_path / "a.whl").write_bytes(b"x")
    # argparse enforces the channel choices
    with pytest.raises(SystemExit):
        um.main(
            [
                "build",
                "--assets",
                str(tmp_path),
                "--version",
                "1.0.0",
                "--channel",
                "bogus",
                "--out",
                str(tmp_path / "o"),
            ]
        )


def test_cli_build_verify_roundtrip(tmp_path):
    import RNS

    rid = tmp_path / "id.rid"
    ident = RNS.Identity()
    ident.to_file(str(rid))
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "pkg-1.0.0.AppImage").write_bytes(b"data" * 100)
    out = tmp_path / "rel"

    rc = um.main(
        [
            "build",
            "--assets",
            str(assets),
            "--version",
            "1.0.0",
            "--channel",
            "stable",
            "--identity",
            str(rid),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    rsm_path = out / "update-manifest-stable.rsm"
    assert rsm_path.is_file()
    assert (out / "update.json").is_file()
    assert (out / "pkg-1.0.0.AppImage.blockmap").is_file()
    # update.json is a debug view matching the signed payload
    dbg = json.loads((out / "update.json").read_text())
    assert dbg["version"] == "1.0.0"
    assert dbg["channel"] == "stable"

    rc = um.main(["verify", str(rsm_path), "--signer", ident.hash.hex()])
    assert rc == 0

    other = RNS.Identity()
    rc = um.main(["verify", str(rsm_path), "--signer", other.hash.hex()])
    assert rc == 1


def test_cli_build_unsigned_writes_msgpack(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "pkg.whl").write_bytes(b"x" * 100)
    out = tmp_path / "o"
    rc = um.main(
        [
            "build",
            "--assets",
            str(assets),
            "--version",
            "1.0.0",
            "--channel",
            "beta",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    assert (out / "update-manifest.msgpack").is_file()
    assert not (out / "update-manifest-beta.rsm").exists()


def test_cli_build_empty_assets_fails(tmp_path):
    assets = tmp_path / "empty"
    assets.mkdir()
    rc = um.main(
        [
            "build",
            "--assets",
            str(assets),
            "--version",
            "1.0.0",
            "--channel",
            "stable",
            "--out",
            str(tmp_path / "o"),
        ]
    )
    assert rc == 1
