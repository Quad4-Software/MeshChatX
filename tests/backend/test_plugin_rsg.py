# SPDX-License-Identifier: 0BSD

import pytest
import RNS

from meshchatx.src.backend.plugin_rsg import (
    RSGError,
    create_rsg,
    validate_rsg,
    verify_rsg_payload,
)
from meshchatx.src.backend.plugin_trusted_publishers import (
    add_user_trusted_publisher,
    list_trusted_publishers,
    lookup_trusted_publisher_in_storage,
)


def test_validate_rsg_roundtrip():
    identity = RNS.Identity()
    message = b"canonical-plugin-payload"
    rsg = create_rsg(message, identity)
    signer = validate_rsg(rsg, message)
    assert signer == identity.hash.hex()


def test_validate_rsg_wrong_hash():
    identity = RNS.Identity()
    rsg = create_rsg(b"payload-a", identity)
    with pytest.raises(RSGError, match="hash"):
        validate_rsg(rsg, b"payload-b")


def test_validate_rsg_truncated():
    with pytest.raises(RSGError, match="too short"):
        validate_rsg(b"short", b"payload")


def test_verify_rsg_payload_and_trusted_lookup(tmp_path):
    identity = RNS.Identity()
    message = b"payload"
    rsg = create_rsg(message, identity)
    info = verify_rsg_payload(rsg, message)
    assert info.present is True
    assert info.valid is True
    assert info.signer == identity.hash.hex()

    db = tmp_path / "state.db"
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    add_user_trusted_publisher(
        str(plugins_root), str(db), identity.hash.hex(), "Example Publisher"
    )
    pubs = list_trusted_publishers(str(plugins_root), str(db))
    assert any(p["identity"] == identity.hash.hex() for p in pubs)
    name, trusted = lookup_trusted_publisher_in_storage(
        identity.hash.hex(), str(plugins_root), str(db)
    )
    assert trusted is True
    assert name == "Example Publisher"
