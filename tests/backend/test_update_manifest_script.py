# SPDX-License-Identifier: 0BSD

"""Tests for scripts/build/update_manifest.py classification and CLI."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "build" / "update_manifest.py"
)
_spec = importlib.util.spec_from_file_location("update_manifest", _SCRIPT)
um = importlib.util.module_from_spec(_spec)
sys.modules["update_manifest"] = um
_spec.loader.exec_module(um)


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
    m = um.build_manifest(tmp_path, version="1.0.0", tag="v1.0.0", track="release")
    assert m["schema"] == 1
    assert m["app"] == "reticulum-meshchatx"
    assert len(m["artifacts"]) == 1
    assert m["artifacts"][0]["sha256"]
    assert m["artifacts"][0]["size"] == 7


def test_build_manifest_rejects_bad_track(tmp_path):
    (tmp_path / "a.whl").write_bytes(b"x")
    with pytest.raises(SystemExit):
        um.build_manifest(tmp_path, version="1", tag="v1", track="bogus")


def test_cli_sign_verify_roundtrip(tmp_path, capsys):
    import RNS

    rid = tmp_path / "id.rid"
    ident = RNS.Identity()
    ident.to_file(str(rid))
    (tmp_path / "pkg-1.0.0.AppImage").write_bytes(b"data")

    rc = um.main(
        [
            "sign",
            "--assets",
            str(tmp_path),
            "--version",
            "1.0.0",
            "--tag",
            "v1.0.0",
            "--track",
            "release",
            "--identity",
            str(rid),
        ]
    )
    assert rc == 0
    assert (tmp_path / "update.rsm").is_file()
    assert (tmp_path / "update.json").is_file()

    rc = um.main(["verify", str(tmp_path / "update.rsm"), "--signer", ident.hash.hex()])
    assert rc == 0

    # wrong signer must fail
    other = RNS.Identity()
    rc = um.main(["verify", str(tmp_path / "update.rsm"), "--signer", other.hash.hex()])
    assert rc == 1


def test_cli_build_empty_assets_fails(tmp_path):
    rc = um.main(
        [
            "build",
            "--assets",
            str(tmp_path),
            "--version",
            "1.0.0",
            "--tag",
            "v1",
            "--track",
            "release",
        ]
    )
    assert rc == 1
