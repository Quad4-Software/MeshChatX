# SPDX-License-Identifier: 0BSD

"""Tests for AutoInterface bind-failure detection in user guidance.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat


def _make_app(config_interfaces):
    """Build a minimal app stub exposing only what the helpers touch."""
    app = SimpleNamespace()
    app.reticulum = SimpleNamespace(
        config={"interfaces": dict(config_interfaces)},
        transport_enabled=lambda: True,
    )
    app._get_interfaces_section = (
        ReticulumMeshChat._get_interfaces_section.__get__(app)
    )
    app._detect_failed_autointerfaces = (
        ReticulumMeshChat._detect_failed_autointerfaces.__get__(app)
    )
    return app


class _FakeAutoInterface:
    pass


_FakeAutoInterface.__name__ = "AutoInterface"


class _FakeTCPClientInterface:
    pass


_FakeTCPClientInterface.__name__ = "TCPClientInterface"


def test_detects_enabled_autointerface_that_failed_to_start():
    app = _make_app(
        {
            "Default Interface": {"type": "AutoInterface", "enabled": "yes"},
        },
    )
    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = []
        assert app._detect_failed_autointerfaces() == ["Default Interface"]


def test_running_autointerface_is_not_reported():
    app = _make_app(
        {
            "Default Interface": {"type": "AutoInterface", "enabled": "yes"},
        },
    )
    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = [_FakeAutoInterface()]
        assert app._detect_failed_autointerfaces() == []


def test_disabled_autointerface_is_ignored():
    app = _make_app(
        {
            "Default Interface": {"type": "AutoInterface", "enabled": "no"},
        },
    )
    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = []
        assert app._detect_failed_autointerfaces() == []


def test_non_auto_interface_does_not_trigger_warning():
    app = _make_app(
        {
            "Hub": {
                "type": "TCPClientInterface",
                "enabled": "yes",
                "target_host": "127.0.0.1",
                "target_port": "4242",
            },
        },
    )
    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = [_FakeTCPClientInterface()]
        assert app._detect_failed_autointerfaces() == []


def test_empty_interfaces_section_is_safe():
    app = _make_app({})
    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = []
        assert app._detect_failed_autointerfaces() == []


def test_guidance_message_emitted_for_failed_autointerface():
    app = _make_app(
        {
            "Default Interface": {"type": "AutoInterface", "enabled": "yes"},
        },
    )
    app.config = MagicMock()
    app.config.auto_announce_enabled.get.return_value = True
    app.build_user_guidance_messages = (
        ReticulumMeshChat.build_user_guidance_messages.__get__(app)
    )

    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = []
        guidance = app.build_user_guidance_messages()

    autointerface_msgs = [g for g in guidance if g["id"] == "autointerface_bind_failed"]
    assert len(autointerface_msgs) == 1
    msg = autointerface_msgs[0]
    assert msg["severity"] == "warning"
    assert msg["action_route"] == "/interfaces"
    assert "Default Interface" in msg["description"]
    assert "Sideband" in msg["description"]


def test_guidance_message_absent_when_autointerface_running():
    app = _make_app(
        {
            "Default Interface": {"type": "AutoInterface", "enabled": "yes"},
        },
    )
    app.config = MagicMock()
    app.config.auto_announce_enabled.get.return_value = True
    app.build_user_guidance_messages = (
        ReticulumMeshChat.build_user_guidance_messages.__get__(app)
    )

    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = [_FakeAutoInterface()]
        guidance = app.build_user_guidance_messages()

    assert not any(g["id"] == "autointerface_bind_failed" for g in guidance)


@pytest.mark.parametrize("enabled_value", ["yes", "true", "1", "Yes", "TRUE"])
def test_truthy_enabled_values_are_recognised(enabled_value):
    app = _make_app(
        {
            "Default Interface": {
                "type": "AutoInterface",
                "enabled": enabled_value,
            },
        },
    )
    with patch("meshchatx.meshchat.RNS.Transport") as transport:
        transport.interfaces = []
        assert app._detect_failed_autointerfaces() == ["Default Interface"]
