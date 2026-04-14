from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.announce_manager import AnnounceManager


@pytest.mark.parametrize(
    "aspect",
    ["lxmf.delivery", "nomadnetwork.node", "lxmf.propagation", "unknown.aspect"],
)
@pytest.mark.parametrize("app_data", [None, b"", b"app_data", b"x" * 500])
def test_upsert_announce_fuzz_aspect_and_app_data(aspect, app_data):
    mock_db = MagicMock()
    mock_db.provider = MagicMock()
    mock_db.announces = MagicMock()
    manager = AnnounceManager(mock_db)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    dest = b"dest_hash_16_bytes!!"
    packet_hash = b"packet_hash_16!!" if app_data is not None else None

    manager.upsert_announce(reticulum, identity, dest, aspect, app_data, packet_hash)

    mock_db.announces.upsert_announce.assert_called_once()
    args, _ = mock_db.announces.upsert_announce.call_args
    data = args[0]
    assert data["aspect"] == aspect
    assert data["destination_hash"] == dest.hex()


@pytest.mark.parametrize(
    "max_stored",
    [None, 0, 1, 10, 1000, 999_999],
)
def test_announce_max_stored_config_fuzz(max_stored):
    mock_db = MagicMock()
    mock_db.announces = MagicMock()
    config = MagicMock()
    config.announce_max_stored_lxmf_delivery = MagicMock()
    config.announce_max_stored_lxmf_delivery.get.return_value = max_stored
    config.announce_max_stored_nomadnetwork_node = MagicMock()
    config.announce_max_stored_lxmf_propagation = MagicMock()

    manager = AnnounceManager(mock_db, config)
    reticulum = MagicMock()
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"new_dest", "lxmf.delivery", b"app_data", b"packet",
    )

    mock_db.announces.upsert_announce.assert_called_once()
    if max_stored is not None and max_stored >= 1:
        mock_db.announces.trim_announces_for_aspect.assert_called_once()
        cap = min(max_stored, 1_000_000)
        mock_db.announces.trim_announces_for_aspect.assert_called_with(
            "lxmf.delivery",
            cap,
        )
    else:
        mock_db.announces.trim_announces_for_aspect.assert_not_called()
