# SPDX-License-Identifier: 0BSD

"""Tests for management identity helpers and ACL parsing."""

import os

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.management_identities import (
    create_management_identity,
    list_management_identities,
    resolve_identity_path,
)


def test_parse_rns_hash_list_accepts_csv_and_lines():
    hashes = ReticulumMeshChat._parse_rns_hash_list(
        "aabbccddeeff00112233445566778899, 00112233445566778899aabbccddeeff",
    )
    assert hashes == [
        "aabbccddeeff00112233445566778899",
        "00112233445566778899aabbccddeeff",
    ]


def test_parse_rns_hash_list_rejects_bad_length():
    with pytest.raises(ValueError, match="hexadecimal"):
        ReticulumMeshChat._parse_rns_hash_list("deadbeef")


def test_create_and_list_management_identities(tmp_path):
    created = create_management_identity(str(tmp_path), "mgmt")
    assert created["name"] == "mgmt"
    assert os.path.isfile(created["path"])
    assert len(created["hash"]) == 32

    listed = list_management_identities(str(tmp_path))
    assert any(item["name"] == "mgmt" for item in listed)

    resolved = resolve_identity_path(str(tmp_path), identity_name="mgmt")
    assert resolved == os.path.realpath(created["path"])

    identity = RNS.Identity.from_file(resolved)
    assert identity is not None
    assert identity.hash.hex() == created["hash"]


def test_create_management_identity_rejects_bad_name(tmp_path):
    with pytest.raises(ValueError, match="Identity name"):
        create_management_identity(str(tmp_path), "../evil")


def test_resolve_identity_path_jailed_to_identities_dir(tmp_path):
    created = create_management_identity(str(tmp_path), "mgmt")
    outside = tmp_path / "outside_identity"
    RNS.Identity().to_file(str(outside))

    assert resolve_identity_path(str(tmp_path), identity_path=created["path"]) == (
        os.path.realpath(created["path"])
    )

    with pytest.raises((PermissionError, FileNotFoundError, ValueError)):
        resolve_identity_path(str(tmp_path), identity_path=str(outside))

    with pytest.raises((PermissionError, FileNotFoundError, ValueError)):
        resolve_identity_path(
            str(tmp_path),
            identity_path=os.path.join(str(tmp_path), "..", "outside_identity"),
        )


def test_resolve_identity_path_rejects_symlink_escape(tmp_path):
    create_management_identity(str(tmp_path), "mgmt")
    identities = tmp_path / "storage" / "identities"
    bait = tmp_path / "bait_key"
    bait.write_bytes(b"not-a-real-key-but-a-file")
    link = identities / "linked"
    try:
        link.symlink_to(bait)
    except OSError:
        pytest.skip("symlink not supported on this filesystem")

    with pytest.raises((PermissionError, FileNotFoundError, ValueError, OSError)):
        resolve_identity_path(str(tmp_path), identity_path=str(link))
