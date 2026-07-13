# SPDX-License-Identifier: 0BSD

"""Regression guards for call contact matching and Codec2/profile selection.

These lock in bugs that broke real calls:
1. Contacts saved under LXMF destination hashes were rejected by contacts-only.
2. Configured audio profiles never reached LXST ``telephone.call()``.
3. Invalid legacy profile id ``2`` silently mapped to Opus instead of a real profile.
4. Codec2 profiles crashed or were unusable when pycodec2/libcodec2 was missing.
5. Incoming calls during outbound dial left the remote ringing forever.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.contacts import ContactsDAO
from meshchatx.src.backend.database.provider import DatabaseProvider
from meshchatx.src.backend.database.schema import DatabaseSchema
from meshchatx.src.backend.telephone_manager import TelephoneManager

pytest.importorskip("LXST")
from LXST.Primitives.Telephony import Profiles

IDENTITY = "a1" * 16
LXMF = "b2" * 16
LXST = "c3" * 16
CALLER_HASH_HEX = IDENTITY


@pytest.fixture
def contacts_dao():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    provider = DatabaseProvider(path)
    DatabaseSchema(provider).initialize()
    yield ContactsDAO(provider)
    provider.close()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def config_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    database.initialize()
    yield database
    database.close()
    if os.path.exists(path):
        os.remove(path)


def _caller_identity():
    ident = MagicMock()
    ident.hash = bytes.fromhex(CALLER_HASH_HEX)
    return ident


def _policy_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    tm = MagicMock()
    tm.initiation_status = None
    tm.telephone = MagicMock()
    ctx.telephone_manager = tm
    ctx.config = MagicMock()
    ctx.database = MagicMock()
    ctx.database.announces.get_announce_by_hash.return_value = None
    ctx.database.announces.get_announces_by_identity_hash.return_value = []
    ctx.voicemail_manager = MagicMock()
    app.current_context = ctx
    app.is_destination_blocked = MagicMock(return_value=False)
    app.websocket_broadcast = MagicMock()
    app.get_name_for_identity_hash = MagicMock(return_value="Caller")
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=LXMF)
    app.get_lxst_telephony_hash_for_identity_hash = MagicMock(return_value=LXST)
    return app


class TestContactsOnlyIdentityVsLxmfRegression:
    """Chat UI often stores LXMF dest as remote_identity_hash; calls use identity hash."""

    def test_dao_matches_identity_via_related_lxmf_hash(self, contacts_dao):
        # Broken historical save: LXMF destination used as primary key
        contacts_dao.add_contact("Friend", LXMF, lxmf_address=LXMF)
        assert contacts_dao.get_contact_by_identity_hash(IDENTITY) is None
        matched = contacts_dao.get_contact_by_identity_hash(
            IDENTITY,
            related_hashes=[LXMF],
        )
        assert matched is not None
        assert matched["name"] == "Friend"

    def test_is_contact_true_for_identity_when_saved_as_lxmf(self):
        contact = {"id": 1, "name": "Friend", "remote_identity_hash": LXMF}

        def lookup(primary, related_hashes=None):
            keys = {primary, *(related_hashes or ())}
            if LXMF in keys:
                return contact
            return None

        app = ReticulumMeshChat.__new__(ReticulumMeshChat)
        ctx = MagicMock()
        ctx.database = MagicMock()
        ctx.database.announces.get_announce_by_hash.return_value = None
        ctx.database.announces.get_announces_by_identity_hash.return_value = [
            {
                "destination_hash": LXMF,
                "identity_hash": IDENTITY,
                "aspect": "lxmf.delivery",
            },
        ]
        ctx.database.contacts.get_contact_by_identity_hash.side_effect = lookup
        app.current_context = ctx
        app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=LXMF)
        app.get_lxst_telephony_hash_for_identity_hash = MagicMock(return_value=LXST)

        assert app._is_contact(IDENTITY) is True

    def test_incoming_contacts_only_allows_lxmf_saved_contact(self):
        app = _policy_app()
        app.config.do_not_disturb_enabled.get.return_value = False
        app.config.telephone_allow_calls_from_contacts_only.get.return_value = True
        app.config.block_all_from_strangers.get.return_value = False
        app.config.telephone_enabled.get.return_value = True
        app.current_context.database.announces.get_announces_by_identity_hash.return_value = [
            {
                "destination_hash": LXMF,
                "identity_hash": IDENTITY,
                "aspect": "lxmf.delivery",
            },
        ]

        def lookup(primary, related_hashes=None):
            keys = {primary, *(related_hashes or ())}
            if LXMF in keys or IDENTITY in keys:
                return {"id": 1, "name": "Friend", "remote_identity_hash": LXMF}
            return None

        app.current_context.database.contacts.get_contact_by_identity_hash.side_effect = lookup
        caller = _caller_identity()

        with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
            async_utils.run_async = MagicMock()
            ReticulumMeshChat.on_incoming_telephone_call(app, caller)

        app.current_context.voicemail_manager.handle_incoming_call.assert_called_once()
        app.current_context.telephone_manager.telephone.hangup.assert_not_called()
        async_utils.run_async.assert_called_once()


class TestIncomingWhileDialingRegression:
    def test_rejects_with_hangup_instead_of_silent_ignore(self):
        app = _policy_app()
        app.current_context.telephone_manager.initiation_status = "Calling..."
        caller = _caller_identity()

        with patch("meshchatx.meshchat.threading.Timer") as mock_timer:

            def run_timer(delay, fn):
                fn()
                t = MagicMock()
                t.start = MagicMock()
                return t

            mock_timer.side_effect = run_timer
            with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
                async_utils.run_async = MagicMock()
                ReticulumMeshChat.on_incoming_telephone_call(app, caller)

        app.current_context.telephone_manager.telephone.hangup.assert_called_once()
        app.current_context.voicemail_manager.handle_incoming_call.assert_not_called()


class TestAudioProfilePassthroughRegression:
    """LXST switch_profile is a no-op when idle; profile must go to call()."""

    @pytest.mark.asyncio
    async def test_outbound_call_receives_codec2_profile(self):
        tm = TelephoneManager(identity=MagicMock())
        tm.telephone = MagicMock()
        tm.telephone.busy = False
        tm.telephone.call_status = 3
        tm.telephone.active_call = None
        tm._path_poll_interval_s = 0.005
        tm._path_retry_interval_s = 0.01
        tm._status_poll_interval_s = 0.01
        tm.preferred_profile_id = Profiles.BANDWIDTH_LOW
        seen = {}

        def capture_call(identity, profile=None):
            seen["profile"] = profile
            tm.telephone.call_status = 0

        tm.telephone.call.side_effect = capture_call
        destination_hash = bytes.fromhex("aa" * 16)

        with (
            patch(
                "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
                return_value=MagicMock(),
            ),
            patch(
                "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
                return_value=True,
            ),
            patch.object(TelephoneManager, "codec2_available", return_value=True),
            patch(
                "meshchatx.src.backend.telephone_manager.RNS.Destination",
            ) as dest_cls,
        ):
            dest_cls.return_value.hash = destination_hash
            await tm.initiate(destination_hash, timeout_seconds=1)

        assert seen["profile"] == Profiles.BANDWIDTH_LOW

    def test_init_does_not_rely_on_idle_switch_profile(self, tmp_path):
        cfg = MagicMock()
        cfg.telephone_enabled.get.return_value = True
        cfg.telephone_audio_profile_id.get.return_value = Profiles.BANDWIDTH_VERY_LOW

        with (
            patch(
                "meshchatx.src.backend.telephone_manager.Telephone",
            ) as telephone_cls,
            patch.object(TelephoneManager, "codec2_available", return_value=True),
        ):
            telephone = telephone_cls.return_value
            tm = TelephoneManager(
                identity=MagicMock(),
                config_manager=cfg,
                storage_dir=str(tmp_path),
            )
            tm.init_telephone()
            assert tm.preferred_profile_id == Profiles.BANDWIDTH_VERY_LOW
            telephone.switch_profile.assert_not_called()

    def test_invalid_legacy_profile_two_falls_back(self):
        tm = TelephoneManager(identity=MagicMock())
        assert tm.resolve_audio_profile_id(2) == Profiles.DEFAULT_PROFILE

    def test_codec2_unavailable_falls_back_to_opus_default(self):
        tm = TelephoneManager(identity=MagicMock())
        with patch.object(TelephoneManager, "codec2_available", return_value=False):
            assert (
                tm.resolve_audio_profile_id(Profiles.BANDWIDTH_ULTRA_LOW)
                == Profiles.DEFAULT_PROFILE
            )


class TestLegacyProfileMigrationRegression:
    def test_persisted_profile_two_migrates_to_default(self, config_db):
        config = ConfigManager(config_db)
        config.telephone_audio_profile_id.set(2)
        reloaded = ConfigManager(config_db)
        assert reloaded.telephone_audio_profile_id.get() == 64

    def test_fresh_default_is_lxst_default_profile(self, config_db):
        config = ConfigManager(config_db)
        assert config.telephone_audio_profile_id.get() == Profiles.DEFAULT_PROFILE


class TestAndroidCodec2PackagingRegression:
    def test_vendor_wheels_include_libcodec2_for_all_abis(self):
        import zipfile

        import pytest

        vendor = Path(__file__).resolve().parents[2] / "android" / "vendor"
        if not vendor.is_dir():
            pytest.skip("android/vendor not present (gitignored)")
        for abi in ("arm64_v8a", "armeabi_v7a", "x86_64"):
            wheels = sorted(vendor.glob(f"pycodec2-*-android_24_{abi}.whl"))
            if not wheels:
                pytest.skip(f"missing pycodec2 for {abi}")
            with zipfile.ZipFile(wheels[-1]) as zin:
                assert "pycodec2/libcodec2.so" in zin.namelist()
            lib_wheels = sorted(
                vendor.glob(f"chaquopy_libcodec2-*-android_24_{abi}.whl")
            )
            if not lib_wheels:
                pytest.skip(f"missing chaquopy_libcodec2 for {abi}")
            with zipfile.ZipFile(lib_wheels[-1]) as zin:
                assert "chaquopy/lib/libcodec2.so" in zin.namelist()

    def test_android_lxst_get_codec_guards_missing_codec2(self):
        import zipfile

        import pytest

        whl = (
            Path(__file__).resolve().parents[2]
            / "android"
            / "vendor"
            / "lxst-0.4.8-py3-none-any.whl"
        )
        if not whl.is_file():
            pytest.skip("android/vendor/lxst wheel not present (gitignored)")
        with zipfile.ZipFile(whl) as zin:
            telephony = zin.read("LXST/Primitives/Telephony.py").decode()
            codecs_init = zin.read("LXST/Codecs/__init__.py").decode()
        assert "if Codec2 is not None:" in telephony
        assert "_CODEC2_IMPORT_ERROR" in codecs_init

    def test_pycodec2_roundtrip_for_call_codec2_profiles(self):
        import numpy as np
        from LXST.Codecs import Codec2

        assert TelephoneManager.codec2_available() is True
        for pid in (
            Profiles.BANDWIDTH_ULTRA_LOW,
            Profiles.BANDWIDTH_VERY_LOW,
            Profiles.BANDWIDTH_LOW,
        ):
            codec = Profiles.get_codec(pid)
            assert isinstance(codec, Codec2)
            spf = codec.c2.samples_per_frame()
            pcm = (0.05 * np.sin(np.linspace(0, 4 * np.pi, spf))).astype(np.float32)
            pcm_i16 = (pcm * 32767).astype(np.int16)
            encoded = codec.c2.encode(pcm_i16)
            decoded = codec.c2.decode(encoded)
            assert len(encoded) == codec.c2.bytes_per_frame()
            assert len(decoded) == spf
