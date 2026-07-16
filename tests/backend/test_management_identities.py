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
    assert resolved == created["path"]

    identity = RNS.Identity.from_file(resolved)
    assert identity is not None
    assert identity.hash.hex() == created["hash"]


def test_create_management_identity_rejects_bad_name(tmp_path):
    with pytest.raises(ValueError, match="Identity name"):
        create_management_identity(str(tmp_path), "../evil")
