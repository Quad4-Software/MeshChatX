# SPDX-License-Identifier: 0BSD

"""TelephoneManager LXST call policy: set_allowed, no auto_answer, link cleanup."""

from unittest.mock import MagicMock, patch

from meshchatx.src.backend.telephone_manager import TelephoneManager


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_init_telephone_disables_auto_answer_and_applies_policy(mock_tel_class, tmp_path):
    storage_dir = tmp_path / "tel"
    storage_dir.mkdir()
    cfg = MagicMock()
    cfg.telephone_enabled.get.return_value = True
    cfg.telephone_audio_profile_id.get.return_value = 64

    phone = MagicMock()
    phone.links = {}
    phone._Telephone__link_closed = MagicMock()
    mock_tel_class.return_value = phone

    tm = TelephoneManager(MagicMock(), config_manager=cfg, storage_dir=str(storage_dir))
    tm.set_call_policy(
        allowed_fn=lambda _h: True,
        blocked_identity_hashes=[b"\x11" * 16],
    )
    tm.init_telephone()

    assert mock_tel_class.call_args.kwargs.get("auto_answer") is None
    assert phone.auto_answer is None
    phone.set_allowed.assert_called()
    phone.set_blocked.assert_called()
    assert callable(phone.set_allowed.call_args[0][0])


@patch("meshchatx.src.backend.telephone_manager.Telephone")
def test_refresh_call_policy_contacts_only_callback(mock_tel_class, tmp_path):
    storage_dir = tmp_path / "tel"
    storage_dir.mkdir()
    cfg = MagicMock()
    cfg.telephone_enabled.get.return_value = True
    cfg.telephone_audio_profile_id.get.return_value = 64
    phone = MagicMock()
    phone.links = {}
    phone._Telephone__link_closed = MagicMock()
    mock_tel_class.return_value = phone

    tm = TelephoneManager(MagicMock(), config_manager=cfg, storage_dir=str(storage_dir))
    tm.init_telephone()

    friend = b"\xaa" * 16
    stranger = b"\xbb" * 16

    def allowed(identity_hash: bytes) -> bool:
        return identity_hash == friend

    tm.set_call_policy(allowed_fn=allowed)
    fn = phone.set_allowed.call_args[0][0]
    assert fn(friend) is True
    assert fn(stranger) is False
    assert phone.auto_answer is None


def test_install_link_cleanup_pops_closed_links():
    tm = TelephoneManager(identity=MagicMock())
    phone = MagicMock()
    phone.links = {"lid": object()}
    previous = MagicMock()
    phone._Telephone__link_closed = previous
    tm.telephone = phone
    tm._install_link_table_cleanup()

    link = MagicMock()
    link.link_id = "lid"
    phone._Telephone__link_closed(link)

    previous.assert_called_once_with(link)
    assert "lid" not in phone.links


def test_sync_telephone_call_policy_wires_allowed_fn():
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    tm = MagicMock()
    ctx.telephone_manager = tm
    ctx.config.do_not_disturb_enabled.get.return_value = False
    ctx.config.telephone_allow_calls_from_contacts_only.get.return_value = True
    ctx.config.block_all_from_strangers.get.return_value = False
    ctx.database.misc.get_blocked_destinations.return_value = []
    app.current_context = ctx
    app.is_destination_blocked = MagicMock(return_value=False)
    app._is_contact = MagicMock(side_effect=lambda h, context=None: h == "aa" * 16)

    app.sync_telephone_call_policy(context=ctx)

    tm.set_call_policy.assert_called_once()
    kwargs = tm.set_call_policy.call_args.kwargs
    allowed = kwargs["allowed_fn"]
    assert allowed(bytes.fromhex("aa" * 16)) is True
    assert allowed(bytes.fromhex("bb" * 16)) is False

    ctx.config.do_not_disturb_enabled.get.return_value = True
    assert allowed(bytes.fromhex("aa" * 16)) is False
