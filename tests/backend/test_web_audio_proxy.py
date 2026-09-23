# SPDX-License-Identifier: 0BSD

"""LazyWebAudioBridge defers LXST/numpy import and isolates failures."""

from __future__ import annotations

import ast
import pathlib

import pytest

from meshchatx.src.backend.web_audio_proxy import LazyWebAudioBridge

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

HEAVY_MODULES = {"LXST", "numpy", "scipy"}


class FakeConfig:
    def __init__(self, web_audio=False, allow_fallback=True):
        class _Opt:
            def __init__(self, value):
                self._value = value

            def get(self):
                return self._value

        self.telephone_web_audio_enabled = _Opt(web_audio)
        self.telephone_web_audio_allow_fallback = _Opt(allow_fallback)


class FakeBridge:
    def __init__(self, telephone_manager, config_manager, force_enabled):
        self.telephone_manager = telephone_manager
        self.config_manager = config_manager
        self.force_enabled = force_enabled
        self.clients = set()
        self.attach_result = True
        self.raise_on = set()
        self.calls = []
        self.ended = 0

    def _maybe_raise(self, name):
        self.calls.append(name)
        if name in self.raise_on:
            raise RuntimeError(f"boom:{name}")

    def attach_client(self, client):
        self._maybe_raise("attach_client")
        self.clients.add(client)
        return self.attach_result

    def detach_client(self, client):
        self._maybe_raise("detach_client")
        self.clients.discard(client)

    def push_client_frame(self, data):
        self._maybe_raise("push_client_frame")

    def on_call_ended(self):
        self._maybe_raise("on_call_ended")
        self.clients.clear()
        self.ended += 1

    async def send_status(self, client):
        self._maybe_raise("send_status")
        await client.send_str('{"type": "web_audio.ready"}')

    def get_diagnostics(self):
        self._maybe_raise("get_diagnostics")
        return {"client_count": len(self.clients)}


def make_proxy(**kwargs):
    made = []
    factory_args = []

    def factory(tm, cfg, force):
        factory_args.append((tm, cfg, force))
        bridge = FakeBridge(tm, cfg, force)
        made.append(bridge)
        return bridge

    proxy = LazyWebAudioBridge(bridge_factory=factory)
    return proxy, made, factory_args


def test_construction_is_deferred():
    proxy, made, _ = make_proxy()
    proxy.configure(object(), FakeConfig(), force_enabled=False)
    proxy.config_enabled()
    proxy.allow_fallback()
    proxy.get_diagnostics()
    proxy.on_call_ended()
    proxy.detach_client(object())
    proxy.push_client_frame(b"\x00" * 128)
    assert made == []
    assert proxy.initialized is False
    assert len(proxy.clients) == 0


def test_attach_client_constructs_and_delegates():
    proxy, made, args = make_proxy()
    tm, cfg = object(), FakeConfig()
    proxy.configure(tm, cfg, force_enabled=True)
    client = object()
    assert proxy.attach_client(client) is True
    assert len(made) == 1
    assert args == [(tm, cfg, True)]
    assert client in made[0].clients
    assert client in proxy.clients


def test_config_reads_do_not_construct():
    proxy, made, _ = make_proxy()
    proxy.configure(None, FakeConfig(web_audio=True), force_enabled=False)
    assert proxy.config_enabled() is True
    assert proxy.allow_fallback() is True
    assert made == []

    proxy.configure(None, FakeConfig(), force_enabled=True)
    assert proxy.config_enabled() is True
    assert proxy.allow_fallback() is False


def test_construction_failure_degrades_permanently():
    def bad_factory(tm, cfg, force):
        raise RuntimeError("lxst import exploded")

    proxy = LazyWebAudioBridge(bridge_factory=bad_factory)
    proxy.configure(None, FakeConfig())
    assert proxy.attach_client(object()) is False
    assert proxy.failed is True
    assert isinstance(proxy.last_error, RuntimeError)
    # Every later call is a no-op, not another exception.
    proxy.push_client_frame(b"x")
    proxy.on_call_ended()
    diag = proxy.get_diagnostics()
    assert diag["failed"] is True
    assert "lxst import exploded" in diag["last_error"]


def test_runtime_failures_trip_circuit_breaker():
    proxy, made, _ = make_proxy()
    proxy.configure(None, FakeConfig())
    assert proxy.attach_client(object()) is True
    bridge = made[0]
    bridge.raise_on.add("push_client_frame")

    for _ in range(2):
        proxy.push_client_frame(b"x")
        assert proxy.failed is False
    proxy.push_client_frame(b"x")
    assert proxy.failed is True
    assert proxy._bridge is None
    # Failed state is terminal: calls are no-ops and clients cleared.
    assert bridge.ended == 1
    assert len(proxy.clients) == 0


def test_recovering_call_resets_failure_count():
    proxy, made, _ = make_proxy()
    proxy.configure(None, FakeConfig())
    proxy.attach_client(object())
    bridge = made[0]
    bridge.raise_on.add("push_client_frame")
    proxy.push_client_frame(b"x")
    proxy.push_client_frame(b"x")
    assert proxy._failure_count == 2
    bridge.raise_on.clear()
    proxy.push_client_frame(b"x")
    assert proxy._failure_count == 0


def test_configure_rebind_tears_down_old_bridge():
    proxy, made, args = make_proxy()
    proxy.configure(object(), FakeConfig())
    proxy.attach_client(object())
    assert len(made) == 1

    new_tm = object()
    proxy.configure(new_tm, FakeConfig(), force_enabled=True)
    assert made[0].ended == 1
    assert proxy.initialized is False

    proxy.attach_client(object())
    assert len(made) == 2
    assert args[-1] == (new_tm, proxy.config_manager, True)


def test_configure_resets_failure_state():
    def bad_factory(tm, cfg, force):
        raise RuntimeError("still broken")

    proxy = LazyWebAudioBridge(bridge_factory=bad_factory)
    proxy.configure(None, FakeConfig())
    proxy.attach_client(object())
    assert proxy.failed is True

    def ok_factory(tm, cfg, force):
        return FakeBridge(tm, cfg, force)

    proxy._bridge_factory = ok_factory
    proxy.configure(None, FakeConfig())
    assert proxy.failed is False
    assert proxy.attach_client(object()) is True


def test_attribute_probe_never_constructs():
    proxy, made, _ = make_proxy()
    assert hasattr(proxy, "nonexistent_method") is False
    assert hasattr(proxy, "get_diagnostics") is True
    assert made == []


def test_shutdown_releases_bridge():
    proxy, made, _ = make_proxy()
    proxy.configure(None, FakeConfig())
    proxy.attach_client(object())
    proxy.shutdown()
    assert made[0].ended == 1
    assert proxy.initialized is False


@pytest.mark.asyncio
async def test_send_status_constructs_and_delegates():
    sent = []

    class FakeWS:
        async def send_str(self, payload):
            sent.append(payload)

    proxy, made, _ = make_proxy()
    proxy.configure(None, FakeConfig(), force_enabled=True)
    await proxy.send_status(FakeWS())
    assert len(made) == 1
    assert sent == ['{"type": "web_audio.ready"}']


@pytest.mark.asyncio
async def test_send_status_survives_construction_failure():
    sent = []

    class FakeWS:
        async def send_str(self, payload):
            sent.append(payload)

    def bad_factory(tm, cfg, force):
        raise RuntimeError("no audio stack")

    proxy = LazyWebAudioBridge(bridge_factory=bad_factory)
    proxy.configure(None, FakeConfig(), force_enabled=True)
    await proxy.send_status(FakeWS())
    assert proxy.failed is True
    assert len(sent) == 1
    assert "web_audio.ready" in sent[0]
    assert '"degraded": true' in sent[0]


def _top_level_imports(path):
    tree = ast.parse(path.read_text())
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize(
    "rel",
    [
        "meshchatx/src/backend/telephone_manager.py",
        "meshchatx/src/backend/voicemail_manager.py",
        "meshchatx/src/backend/web_audio_proxy.py",
        "meshchatx/meshchat.py",
    ],
)
def test_no_module_level_audio_imports(rel):
    # LXST and numpy must stay out of module-level imports so text-only
    # installs never pay the audio stack's import cost.
    top = _top_level_imports(REPO_ROOT / rel)
    assert top.isdisjoint(HEAVY_MODULES), (
        f"{rel} imports {top & HEAVY_MODULES} at module level"
    )
