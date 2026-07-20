# SPDX-License-Identifier: 0BSD

"""Plugin capability and hook coverage for the generic RNS Link API."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


def _make_manager(tmp_path, app=None):
    from meshchatx.src.backend.plugin_manager import PluginManager

    return PluginManager(str(tmp_path), app=app)


def _enable_with_link_perms(manager, plugin_id, *, managers=None, hooks=None):
    manager.enable(plugin_id)
    record = manager._plugins[plugin_id]
    perms = record.manifest.setdefault("permissions", {})
    granted = list(record.granted_permissions or [])
    if managers is not None:
        perms["managers"] = managers
        for manager_name in managers:
            perm_id = f"managers:{manager_name}"
            if perm_id not in granted:
                granted.append(perm_id)
    if hooks is not None:
        perms["hooks"] = hooks
        for hook in hooks:
            perm_id = f"hooks:{hook}"
            if perm_id not in granted:
                granted.append(perm_id)
    record.granted_permissions = granted
    return record


class FakeLinkManager:
    def __init__(self):
        self.opened = []
        self.identified = []
        self.sent = []
        self.closed = []
        self.requested = []

    async def open_link(self, dest_hash, aspect, *, auto_identify=False, on_phase=None):
        self.opened.append((dest_hash, aspect, auto_identify))
        if on_phase:
            on_phase("establishing_link")
        return object(), bool(auto_identify), None

    def identify(self, dest_hash, aspect):
        self.identified.append((dest_hash, aspect))
        return True, None

    def send_packet(self, dest_hash, aspect, payload):
        self.sent.append((dest_hash, aspect, payload))
        return True, None

    def close(self, dest_hash, aspect):
        self.closed.append((dest_hash, aspect))
        return True

    def request(
        self,
        dest_hash,
        aspect,
        path,
        data,
        response_callback,
        failed_callback,
        progress_callback,
        timeout=None,
    ):
        self.requested.append((dest_hash, aspect, path, data, timeout))
        receipt = MagicMock()
        receipt.response = {"ok": True, "path": path}
        response_callback(receipt)
        return receipt


class TestRnsLinkPluginCapabilities:
    def test_all_capabilities_roundtrip(self, tmp_path):
        fake = FakeLinkManager()

        class FakeApp:
            reticulum = object()
            rns_link_manager = fake

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        _enable_with_link_perms(
            manager,
            plugin_id,
            managers=[
                "rnsLink.open",
                "rnsLink.identify",
                "rnsLink.request",
                "rnsLink.send",
                "rnsLink.close",
            ],
        )
        dest = "aa" * 16
        aspect = "microrn.mgmt"
        opened = manager.call_manager(
            plugin_id,
            "rnsLink.open",
            {"destination_hash": dest, "aspect": aspect, "auto_identify": True},
        )
        assert opened["ok"] is True
        assert opened["identified"] is True

        identified = manager.call_manager(
            plugin_id,
            "rnsLink.identify",
            {"destination_hash": dest, "aspect": aspect},
        )
        assert identified["ok"] is True

        from RNS.vendor import umsgpack

        body = umsgpack.packb({"cmd": "status"})
        requested = manager.call_manager(
            plugin_id,
            "rnsLink.request",
            {
                "destination_hash": dest,
                "aspect": aspect,
                "path": "/status",
                "data_b64": base64.b64encode(body).decode("ascii"),
                "timeout": 1,
            },
        )
        assert requested["ok"] is True
        assert "body_b64" in requested

        sent = manager.call_manager(
            plugin_id,
            "rnsLink.send",
            {
                "destination_hash": dest,
                "aspect": aspect,
                "payload_b64": base64.b64encode(b"hi").decode("ascii"),
            },
        )
        assert sent["ok"] is True

        closed = manager.call_manager(
            plugin_id,
            "rnsLink.close",
            {"destination_hash": dest, "aspect": aspect},
        )
        assert closed["ok"] is True
        assert len(fake.opened) == 2  # open + request open
        assert fake.closed

    def test_invalid_args_raise_value_error(self, tmp_path):
        fake = FakeLinkManager()

        class FakeApp:
            reticulum = object()
            rns_link_manager = fake

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        _enable_with_link_perms(
            manager,
            plugin_id,
            managers=["rnsLink.open", "rnsLink.send", "rnsLink.request"],
        )
        with pytest.raises(ValueError):
            manager.call_manager(
                plugin_id,
                "rnsLink.open",
                {"destination_hash": "zz", "aspect": "a"},
            )
        with pytest.raises(ValueError):
            manager.call_manager(
                plugin_id,
                "rnsLink.open",
                {"destination_hash": "aa" * 16},
            )
        with pytest.raises(ValueError):
            manager.call_manager(
                plugin_id,
                "rnsLink.send",
                {
                    "destination_hash": "aa" * 16,
                    "aspect": "a",
                    "payload_b64": "!!!",
                },
            )
        with pytest.raises(ValueError):
            manager.call_manager(
                plugin_id,
                "rnsLink.request",
                {
                    "destination_hash": "aa" * 16,
                    "aspect": "a",
                    "path": "",
                },
            )

    def test_request_open_failure_propagates(self, tmp_path):
        class FailingOpen:
            async def open_link(self, *_args, **_kwargs):
                return None, False, "no_path_to_destination"

        class FakeApp:
            reticulum = object()
            rns_link_manager = FailingOpen()

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        _enable_with_link_perms(manager, plugin_id, managers=["rnsLink.request"])
        result = manager.call_manager(
            plugin_id,
            "rnsLink.request",
            {
                "destination_hash": "aa" * 16,
                "aspect": "microrn.mgmt",
                "path": "/status",
            },
        )
        assert result["ok"] is False
        assert result["failure_reason"] == "no_path_to_destination"

    def test_event_hook_requires_permission(self, tmp_path):
        events = []

        class FakeApp:
            plugins_enabled = True

            def websocket_broadcast(self, _message):
                return None

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        manager.enable(plugin_id)
        manager.dispatch_hook = lambda *args: events.append(args)
        manager.on_rns_link_event(
            {
                "type": "rns.link.event",
                "event": "packet_received",
                "destination_hash": "aa" * 16,
                "aspect": "microrn.mgmt",
                "payload_b64": "AA==",
            },
        )
        assert events == []

        _enable_with_link_perms(
            manager,
            plugin_id,
            hooks=["announce.received", "rns.link.event"],
        )
        manager.on_rns_link_event(
            {
                "type": "rns.link.event",
                "event": "packet_received",
                "destination_hash": "aa" * 16,
                "aspect": "microrn.mgmt",
                "payload_b64": "AA==",
            },
        )
        assert events
        assert events[-1][1] == "rns.link.event"

    @given(
        dest=st.binary(min_size=16, max_size=16).map(lambda b: b.hex()),
        aspect=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz."),
            min_size=1,
            max_size=32,
        ).filter(lambda v: any(ch.isalpha() for ch in v)),
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_open_close_property(self, tmp_path_factory, dest, aspect):
        # Fresh plugin storage per Hypothesis example avoids integrity flakes
        # when a prior example activated Python bytecode under the install tree.
        tmp_path = tmp_path_factory.mktemp("rns_link")
        fake = FakeLinkManager()

        class FakeApp:
            reticulum = object()
            rns_link_manager = fake

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        _enable_with_link_perms(
            manager,
            plugin_id,
            managers=["rnsLink.open", "rnsLink.close"],
        )
        opened = manager.call_manager(
            plugin_id,
            "rnsLink.open",
            {"destination_hash": dest, "aspect": aspect},
        )
        closed = manager.call_manager(
            plugin_id,
            "rnsLink.close",
            {"destination_hash": dest, "aspect": aspect},
        )
        assert opened["ok"] is True
        assert closed["ok"] is True
        assert opened["destination_hash"] == dest
        assert closed["aspect"] == aspect


def test_app_broadcast_fans_out_plugin_events(tmp_path):
    from meshchatx.meshchat import ReticulumMeshChat

    events = []
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.plugin_manager = MagicMock()
    app.plugin_manager.on_rns_link_event = lambda payload: events.append(payload)
    app._broadcast_to_websocket_clients = MagicMock()
    payload = {
        "type": "rns.link.event",
        "event": "link_closed",
        "destination_hash": "aa" * 16,
        "aspect": "microrn.mgmt",
    }
    app._on_rns_link_broadcast(payload)
    app._broadcast_to_websocket_clients.assert_called_once_with(payload)
    assert events == [payload]
