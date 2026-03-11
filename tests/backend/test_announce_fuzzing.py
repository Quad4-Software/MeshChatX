import pytest
from unittest.mock import MagicMock

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
    "limit_val,count,should_accept",
    [
        (None, 100, True),
        (0, 0, False),
        (10, 5, True),
        (10, 10, False),
        (100, 100, False),
        (1000, 0, True),
    ],
)
def test_announce_limit_config_fuzz(limit_val, count, should_accept):
    mock_db = MagicMock()
    mock_db.announces = MagicMock()
    mock_db.announces.get_announce_by_hash.return_value = None
    mock_db.announces.get_announce_count_by_aspect.return_value = count

    config = MagicMock()
    config.announce_limit_lxmf_delivery = MagicMock()
    config.announce_limit_lxmf_delivery.get.return_value = limit_val
    config.announce_limit_nomadnetwork_node = MagicMock()
    config.announce_limit_lxmf_propagation = MagicMock()

    manager = AnnounceManager(mock_db, config)
    reticulum = MagicMock()
    reticulum.get_packet_rssi.return_value = -50
    reticulum.get_packet_snr.return_value = 10
    identity = MagicMock()
    identity.hash.hex.return_value = "id_hash"
    identity.get_public_key.return_value = b"pub_key"

    manager.upsert_announce(
        reticulum, identity, b"new_dest", "lxmf.delivery", b"app_data", b"packet"
    )

    if should_accept:
        mock_db.announces.upsert_announce.assert_called_once()
    else:
        mock_db.announces.upsert_announce.assert_not_called()
