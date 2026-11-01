# SPDX-License-Identifier: 0BSD

"""Failed direct sends drop and re-request the recipient path.

LXMF never expires a stale path when a direct or opportunistic delivery
fails after max attempts, so every retry reuses the dead route. After a
failed send the app drops the cached path and requests a fresh one, rate
limited per destination, so a moved or reconnected peer is rediscovered.
"""

import time
from unittest.mock import MagicMock, patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat

DEST = b"\x11" * 16
LOCAL = b"\x99" * 16


@pytest.fixture
def mock_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.reticulum = MagicMock()
    app._path_refresh_after_failed_send_at = {}
    app.send_failed_message_via_propagation_node = MagicMock()
    app.on_lxmf_sending_state_updated = MagicMock()
    ctx = MagicMock()
    ctx.local_lxmf_destination = MagicMock()
    ctx.local_lxmf_destination.hash = LOCAL
    app.current_context = ctx
    return app


def _failed_msg(desired_method=LXMF.LXMessage.DIRECT, propagated=False):
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.state = LXMF.LXMessage.FAILED
    msg.desired_method = desired_method
    msg.destination_hash = DEST
    msg.try_propagation_on_fail = propagated
    return msg


def test_failed_direct_send_drops_and_requests_path(mock_app):
    msg = _failed_msg()
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    mock_app.reticulum.drop_path.assert_called_once_with(DEST)
    request_path.assert_called_once_with(DEST)


def test_propagation_fallback_still_refreshes_original_direct_path(mock_app):
    msg = _failed_msg(propagated=True)

    def fallback(m, context=None):
        m.desired_method = LXMF.LXMessage.PROPAGATED

    mock_app.send_failed_message_via_propagation_node.side_effect = fallback
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    mock_app.reticulum.drop_path.assert_called_once_with(DEST)
    request_path.assert_called_once_with(DEST)


def test_propagated_from_start_does_not_refresh(mock_app):
    msg = _failed_msg(desired_method=LXMF.LXMessage.PROPAGATED)
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    mock_app.reticulum.drop_path.assert_not_called()
    request_path.assert_not_called()


def test_non_failed_state_does_not_refresh(mock_app):
    msg = _failed_msg()
    msg.state = LXMF.LXMessage.SENT
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    mock_app.reticulum.drop_path.assert_not_called()
    request_path.assert_not_called()


def test_refresh_is_rate_limited_per_destination(mock_app):
    msg = _failed_msg()
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
        assert request_path.call_count == 1
        assert mock_app.reticulum.drop_path.call_count == 1

        mock_app._path_refresh_after_failed_send_at[DEST] = time.time() - 61.0
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
        assert request_path.call_count == 2
        assert mock_app.reticulum.drop_path.call_count == 2


def test_drop_path_error_still_requests_path(mock_app):
    mock_app.reticulum.drop_path.side_effect = Exception("rpc timeout")
    msg = _failed_msg()
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    request_path.assert_called_once_with(DEST)


def test_local_destination_is_not_refreshed(mock_app):
    msg = _failed_msg()
    msg.destination_hash = LOCAL
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    mock_app.reticulum.drop_path.assert_not_called()
    request_path.assert_not_called()


def _telemetry_msg_via_fields():
    msg = _failed_msg()
    msg.fields = {LXMF.FIELD_TELEMETRY: b"telemetry"}
    return msg


def _telemetry_msg_via_commands():
    from meshchatx.src.backend.sideband_commands import SidebandCommands

    msg = _failed_msg()
    msg.fields = {
        LXMF.FIELD_COMMANDS: [{SidebandCommands.TELEMETRY_REQUEST: 0}],
    }
    return msg


def test_telemetry_field_does_not_refresh(mock_app):
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, _telemetry_msg_via_fields())
    mock_app.reticulum.drop_path.assert_not_called()
    request_path.assert_not_called()


def test_telemetry_command_does_not_refresh(mock_app):
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(
            mock_app, _telemetry_msg_via_commands()
        )
    mock_app.reticulum.drop_path.assert_not_called()
    request_path.assert_not_called()


def test_unrelated_fields_still_refresh(mock_app):
    msg = _failed_msg()
    msg.fields = {0x05: b"some other field"}
    with patch.object(RNS.Transport, "request_path") as request_path:
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
    mock_app.reticulum.drop_path.assert_called_once_with(DEST)
    request_path.assert_called_once_with(DEST)


def test_global_cap_skips_eleventh_destination(mock_app):
    dests = [bytes([i]) * 16 for i in range(1, 12)]
    with patch.object(RNS.Transport, "request_path") as request_path:
        for dest in dests:
            msg = _failed_msg()
            msg.destination_hash = dest
            ReticulumMeshChat.on_lxmf_sending_failed(mock_app, msg)
        assert request_path.call_count == 10
        assert mock_app.reticulum.drop_path.call_count == 10
        # The skipped destination is not put on per destination cooldown.
        assert dests[-1] not in mock_app._path_refresh_after_failed_send_at
        # After the window slides it refreshes.
        stale = time.time() - 61.0
        recent = mock_app._path_refresh_after_failed_send_recent
        while recent:
            recent.popleft()
        recent.extend([stale] * 10)
        skipped = _failed_msg()
        skipped.destination_hash = dests[-1]
        ReticulumMeshChat.on_lxmf_sending_failed(mock_app, skipped)
        assert request_path.call_count == 11
