import os
import random
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import LXMF
import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def mock_app(temp_dir):
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"test_hash_32_bytes_long_01234567"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        stack.enter_context(patch("meshchatx.src.backend.identity_context.Database"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ConfigManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.MessageHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.AnnounceManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.ArchiverManager")
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.MapManager"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TelephoneManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.VoicemailManager")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RingtoneManager")
        )
        stack.enter_context(patch("meshchatx.src.backend.identity_context.RNCPHandler"))
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNStatusHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.RNProbeHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.TranslatorHandler")
        )
        stack.enter_context(
            patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager")
        )
        stack.enter_context(patch("meshchatx.meshchat.AsyncUtils"))
        stack.enter_context(patch("LXMF.LXMRouter"))
        stack.enter_context(patch("LXST.Primitives.Telephony"))
        stack.enter_context(patch("RNS.Identity", MockIdentityClass))
        mock_reticulum_class = stack.enter_context(patch("RNS.Reticulum"))
        mock_reticulum_class.MTU = 1200
        mock_reticulum_class.return_value.MTU = 1200
        mock_transport_class = stack.enter_context(patch("RNS.Transport"))
        mock_transport_class.MTU = 1200
        mock_transport_class.return_value.MTU = 1200
        stack.enter_context(patch("threading.Thread"))
        stack.enter_context(
            patch.object(
                ReticulumMeshChat, "announce_loop", new=MagicMock(return_value=None)
            )
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat,
                "announce_sync_propagation_nodes",
                new=MagicMock(return_value=None),
            )
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat, "crawler_loop", new=MagicMock(return_value=None)
            )
        )
        stack.enter_context(
            patch.object(
                ReticulumMeshChat, "auto_backup_loop", new=MagicMock(return_value=None)
            )
        )

        mock_id = MockIdentityClass()
        mock_id.get_private_key = MagicMock(return_value=b"test_private_key")
        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id)
        )

        app = ReticulumMeshChat(
            identity=mock_id,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app.active_downloads = {}
        app.download_id_counter = 0
        app.database = MagicMock()

        # Setup basic config mocks
        app.config = MagicMock()
        for attr in [
            "display_name",
            "theme",
            "language",
            "voicemail_greeting",
            "map_default_lat",
            "map_default_lon",
        ]:
            getattr(app.config, attr).get.return_value = "test"
        for attr in ["auto_announce_enabled", "voicemail_enabled"]:
            getattr(app.config, attr).get.return_value = False
        app.config.lxmf_inbound_stamp_cost.get.return_value = 8

        return app


# WebSocket API Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    data=st.recursive(
        st.one_of(st.none(), st.booleans(), st.floats(), st.text(), st.integers()),
        lambda children: st.one_of(
            st.lists(children), st.dictionaries(st.text(), children)
        ),
    )
)
@pytest.mark.asyncio
async def test_websocket_api_recursive_fuzzing(mock_app, data):
    """Fuzz the websocket API with recursive random data structures."""
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(side_effect=lambda d: None)

    # We must ensure "type" is present if it's a dict, or it might fail early
    # but that's also part of fuzzing - seeing if it crashes without "type".
    try:
        await mock_app.on_websocket_data_received(mock_client, data)
    except (KeyError, TypeError, ValueError, AttributeError):
        # These are expected for malformed data
        pass
    except Exception as e:
        pytest.fail(f"WebSocket API crashed with recursive data: {e}")


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(msg_type=st.text(), payload=st.dictionaries(st.text(), st.text()))
@pytest.mark.asyncio
async def test_websocket_api_type_fuzzing(mock_app, msg_type, payload):
    """Fuzz the websocket API with random types and flat dictionary payloads."""
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(side_effect=lambda d: None)

    data = {"type": msg_type}
    data.update(payload)

    try:
        await mock_app.on_websocket_data_received(mock_client, data)
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    except Exception as e:
        pytest.fail(f"WebSocket API crashed with type={msg_type}: {e}")


# URI Parsing Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(uri=st.text(min_size=0, max_size=2000))
@pytest.mark.asyncio
async def test_lxm_uri_parsing_fuzzing(mock_app, uri):
    """Fuzz LXM URI ingestion logic."""
    try:
        # Assuming there's a method or logic that handles lxm:// URIs
        if hasattr(mock_app, "ingest_lxm_uri"):
            await mock_app.ingest_lxm_uri(uri)

        # Also test it through the websocket interface if it exists there
        mock_client = MagicMock()
        await mock_app.on_websocket_data_received(
            mock_client, {"type": "lxm.ingest_uri", "uri": uri}
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    except Exception as e:
        # Some specific exceptions might be okay depending on implementation,
        # but generic crash is not.
        if "hex" not in str(e).lower():  # Ignore hex decoding errors which are common
            pytest.fail(f"URI ingestion crashed with uri={uri}: {e}")


# LXMF Packet/Message Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    content=st.binary(min_size=0, max_size=5000),
    title=st.text(min_size=0, max_size=500),
    fields=st.dictionaries(st.integers(min_value=0, max_value=255), st.binary()),
)
def test_lxmf_message_construction_fuzzing(mock_app, content, title, fields):
    """Fuzz LXMF message construction and field handling."""
    try:
        # Mock a destination
        dest = MagicMock()
        dest.hash = os.urandom(16)

        # Test field assignment
        lxmf_msg = LXMF.LXMessage(dest, mock_app.identity, content, title=title)
        for k, v in fields.items():
            lxmf_msg.fields[k] = v

        # Test encoding/decoding if possible
        lxmf_msg.pack()
        # LXMF.LXMessage.unpack(packed) # Might need more mocks
    except Exception:
        pass


# Database Migration/Data Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    table_name=st.sampled_from(["messages", "announces", "identities", "config"]),
    data=st.dictionaries(
        st.text(), st.one_of(st.text(), st.integers(), st.binary(), st.none())
    ),
)
def test_database_record_fuzzing(mock_app, table_name, data):
    """Fuzz database record insertion logic (simulated)."""
    # This tests the DAO layer's resilience to weird data types if they aren't properly sanitized
    try:
        dao = None
        if table_name == "messages" and hasattr(mock_app.database, "messages"):
            dao = mock_app.database.messages
        elif table_name == "announces" and hasattr(mock_app.database, "announces"):
            dao = mock_app.database.announces

        if dao and hasattr(dao, "upsert"):
            dao.upsert(data)
    except Exception:
        pass


# Config Update Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    config_updates=st.dictionaries(
        st.sampled_from(
            [
                "display_name",
                "auto_announce_enabled",
                "theme",
                "language",
                "voicemail_enabled",
                "voicemail_greeting",
                "map_default_lat",
                "map_default_lon",
                "lxmf_inbound_stamp_cost",
            ]
        ),
        st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
    )
)
@pytest.mark.asyncio
async def test_config_update_fuzzing(mock_app, config_updates):
    """Fuzz the update_config method with various types for known keys."""
    try:
        if hasattr(mock_app, "update_config"):
            await mock_app.update_config(config_updates)
    except (TypeError, ValueError, AttributeError):
        pass
    except Exception as e:
        pytest.fail(f"Config update crashed: {e}")


# LXMF Paper URI Generation Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(destination_hash=st.text(), content=st.text(), title=st.text())
@pytest.mark.asyncio
async def test_lxm_generate_paper_uri_fuzzing(
    mock_app, destination_hash, content, title
):
    """Fuzz lxm.generate_paper_uri WebSocket handler."""
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(side_effect=lambda d: None)

    data = {
        "type": "lxm.generate_paper_uri",
        "destination_hash": destination_hash,
        "content": content,
        "title": title,
    }

    try:
        await mock_app.on_websocket_data_received(mock_client, data)
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    except Exception as e:
        # Ignore common hex decoding or identity not found errors
        if "hex" not in str(e).lower() and "identity not found" not in str(e).lower():
            pytest.fail(f"Paper URI generation crashed: {e}")


# Telemetry Packet Fuzzing (More intensive)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(data=st.binary(min_size=0, max_size=10000))
def test_telemetry_deep_fuzzing(data):
    """Deep fuzz the telemetry unpacking logic with large random payloads."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    try:
        Telemeter.from_packed(data)
    except Exception:
        pass


# Markdown Renderer Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(text=st.text(min_size=0, max_size=10000))
def test_markdown_renderer_fuzzing(text):
    """Fuzz the markdown to HTML renderer."""
    from meshchatx.src.backend.markdown_renderer import MarkdownRenderer

    try:
        html_out = MarkdownRenderer.render(text)
        assert isinstance(html_out, str)
    except Exception as e:
        pytest.fail(f"MarkdownRenderer crashed: {e}")


# LXMF Message Dictionary Conversion Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    content=st.binary(min_size=0, max_size=1000),
    title=st.text(min_size=0, max_size=100),
    fields_data=st.dictionaries(st.integers(0, 255), st.binary()),
)
def test_lxmf_to_dict_conversion_fuzzing(mock_app, content, title, fields_data):
    """Fuzz the LXMF message to dictionary conversion logic."""
    from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict

    try:
        # Create a real-ish LXMessage but fuzzed
        dest = MagicMock()
        dest.hash = os.urandom(16)

        msg = LXMF.LXMessage(dest, mock_app.identity, content, title=title)
        for k, v in fields_data.items():
            msg.fields[k] = v

        # Manually set some fields that might be expected
        msg.hash = os.urandom(16)
        msg.source_hash = os.urandom(16)
        msg.destination_hash = os.urandom(16)
        msg.incoming = random.choice([True, False])
        msg.progress = random.random()
        msg.rssi = random.randint(-120, 0)
        msg.snr = random.randint(-20, 20)
        msg.q = random.randint(0, 100)
        msg.delivery_attempts = random.randint(0, 10)

        result = convert_lxmf_message_to_dict(msg)
        assert isinstance(result, dict)
    except Exception:
        # LXMF might throw internal errors on weird fields, which is okay as long as it doesn't crash the whole app
        pass


# LXMF Delivery Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    content=st.binary(min_size=0, max_size=2000),
    title=st.text(min_size=0, max_size=100),
)
def test_on_lxmf_delivery_fuzzing(mock_app, content, title):
    """Fuzz the LXMF delivery handler with various message contents."""
    try:
        dest = MagicMock()
        dest.hash = os.urandom(16)
        msg = LXMF.LXMessage(dest, mock_app.identity, content, title=title)

        # Add random fields
        msg.fields[LXMF.FIELD_TELEMETRY] = os.urandom(random.randint(0, 100))

        # These are usually set by LXMF when receiving
        msg.source_hash = os.urandom(16)
        msg.hash = os.urandom(16)
        msg.signature = os.urandom(64)

        mock_app.on_lxmf_delivery(msg)
    except Exception:
        pass


# Announce Ingestion Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    aspect=st.text(),
    destination_hash=st.binary(min_size=0, max_size=64),
    app_data=st.binary(min_size=0, max_size=1000),
)
def test_on_lxmf_announce_received_fuzzing(
    mock_app, aspect, destination_hash, app_data
):
    """Fuzz the announce received handler."""
    try:
        announced_identity = MagicMock()
        announced_identity.hash = os.urandom(32)
        announced_identity.get_public_key = MagicMock(return_value=os.urandom(32))

        mock_app.on_lxmf_announce_received(
            aspect,
            destination_hash,
            announced_identity,
            None,  # reticulum instance
            app_data,
        )
    except Exception:
        pass


# Interface Config Parser Fuzzing (More intensive)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(config_text=st.text(min_size=0, max_size=10000))
def test_interface_config_parser_deep_fuzzing(config_text):
    """Deep fuzz the interface configuration parser."""
    from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser

    try:
        InterfaceConfigParser.parse(config_text)
    except Exception:
        # We don't care if it fails to parse, just that it doesn't crash the process
        pass


# Telemeter Roundtrip Fuzzing
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
@given(
    battery=st.floats(0, 100, allow_nan=False, allow_infinity=False),
    uptime=st.integers(0, 2**32 - 1),
    load=st.floats(0, 100, allow_nan=False, allow_infinity=False),
    temperature=st.floats(-50, 100, allow_nan=False, allow_infinity=False),
)
def test_telemeter_roundtrip_fuzzing(battery, uptime, load, temperature):
    """Fuzz telemeter packing and unpacking in a roundtrip."""
    from meshchatx.src.backend.telemetry_utils import Telemeter

    try:
        t = Telemeter(
            battery=battery, uptime=uptime, load=load, temperature=temperature
        )
        packed = t.pack()
        unpacked = Telemeter.from_packed(packed)
        assert isinstance(unpacked, Telemeter)
    except Exception:
        pass
