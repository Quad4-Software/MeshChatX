# SPDX-License-Identifier: 0BSD

"""Tests for RNSh manager HTTP API endpoints and launcher argv."""

import json
from unittest.mock import MagicMock

import pytest


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(json_body=None, match_info=None, query=None):
    request = MagicMock()

    async def _json():
        return json_body if json_body is not None else {}

    request.json = _json
    request.match_info = match_info or {}
    request.query = query or {}
    return request


class _DummySession:
    def __init__(self, session_id="s1", start_error=None):
        self.session_id = session_id
        self._start_error = start_error

    def to_dict(self, include_output_tail=False):
        return {
            "id": self.session_id,
            "name": "test",
            "mode": "connect",
            "status": "running",
            "output_chunks": [],
            "output_text": "",
            "last_command": "rnsh deadbeef",
        }

    def start(self):
        if self._start_error is not None:
            raise self._start_error
        return self.to_dict(include_output_tail=True)


class _DummyManager:
    def __init__(self):
        self.created_payload = None
        self.sent_text = None
        self.removed_ids = []
        self._sessions = {"s2": _DummySession("s2")}

    def list_sessions(self):
        return {"sessions": [_DummySession("s1").to_dict(include_output_tail=True)]}

    def create_session(self, payload):
        self.created_payload = payload
        session = _DummySession("s2")
        self._sessions[session.session_id] = session
        return session

    def remove_session(self, session_id):
        self.removed_ids.append(session_id)
        if session_id == "missing" or session_id not in self._sessions:
            raise KeyError("missing")
        self._sessions.pop(session_id, None)

    def start_session(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")
        return _DummySession(session_id).to_dict(include_output_tail=True)

    def stop_session(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")
        return _DummySession(session_id).to_dict(include_output_tail=True)

    def send_input(self, session_id, text):
        if session_id == "missing":
            raise KeyError("missing")
        self.sent_text = text
        return _DummySession(session_id).to_dict(include_output_tail=False)

    def resize_session(self, session_id, rows, cols):
        if session_id == "missing":
            raise KeyError("missing")
        self.resized = (rows, cols)
        return _DummySession(session_id).to_dict(include_output_tail=False)

    def output_since(self, session_id, cursor):
        if session_id == "missing":
            raise KeyError("missing")
        return {"chunks": [{"seq": 1, "text": "ok", "ts": 1.0}], "next_cursor": 1}

    def clear_output(self, session_id):
        if session_id == "missing":
            raise KeyError("missing")
        return _DummySession(session_id).to_dict(include_output_tail=True)


@pytest.mark.asyncio
async def test_rnsh_list_sessions(mock_app):
    mock_app.rnsh_manager = _DummyManager()
    handler = _find_handler(mock_app, "/api/v1/rnsh/sessions", "GET")
    assert handler is not None
    response = await handler(_make_request())
    assert response.status == 200
    data = json.loads(response.body)
    assert len(data["sessions"]) == 1


@pytest.mark.asyncio
async def test_rnsh_create_and_autostart(mock_app):
    manager = _DummyManager()
    mock_app.rnsh_manager = manager
    handler = _find_handler(mock_app, "/api/v1/rnsh/sessions", "POST")
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={
                "name": "ops",
                "mode": "connect",
                "destination": "00112233445566778899aabbccddeeff",
                "autostart": True,
            },
        ),
    )
    assert response.status == 200
    data = json.loads(response.body)
    assert data["session"]["id"] == "s2"
    assert manager.created_payload["name"] == "ops"


@pytest.mark.asyncio
async def test_rnsh_send_input_appends_newline(mock_app):
    manager = _DummyManager()
    mock_app.rnsh_manager = manager
    handler = _find_handler(
        mock_app, "/api/v1/rnsh/sessions/{session_id}/input", "POST"
    )
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={"text": "ls", "newline": True},
            match_info={"session_id": "s1"},
        ),
    )
    assert response.status == 200
    assert manager.sent_text == "ls\n"


@pytest.mark.asyncio
async def test_rnsh_resize_forwards_dimensions(mock_app):
    manager = _DummyManager()
    mock_app.rnsh_manager = manager
    handler = _find_handler(
        mock_app, "/api/v1/rnsh/sessions/{session_id}/resize", "POST"
    )
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={"rows": 24, "cols": 80},
            match_info={"session_id": "s1"},
        ),
    )
    assert response.status == 200
    assert manager.resized == (24, 80)


def test_rnsh_listen_address_detected_from_output():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    assert session.listen_address == ""
    session.append_output(
        "[Notice] rnsh listening for commands on <8d7f90d560627da94a312bb96ba5c485>\n",
    )
    assert session.listen_address == "8d7f90d560627da94a312bb96ba5c485"

    payload = session.to_dict()
    assert payload["listen_address"] == "8d7f90d560627da94a312bb96ba5c485"


def test_rnsh_listen_address_ignores_verbose_identity_hashes():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    session.append_output(
        "[Verbose]  Identity keys created for <aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa>\n"
        "[Verbose]  Transport instance <bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb> started\n"
        "[Notice]   rnsh listening for commands on <cccccccccccccccccccccccccccccccc>\n",
    )
    assert session.listen_address == "cccccccccccccccccccccccccccccccc"


def test_rnsh_resize_updates_geometry_without_process():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "connect", "destination": "abc"})
    result = session.resize(30, 100)
    assert result["rows"] == 30
    assert result["cols"] == 100


def test_rnsh_prefers_module_launcher_when_rns_installed(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: True)
    monkeypatch.setattr(rnsh_mod.RNSHSession, "_is_frozen_executable", lambda: False)
    monkeypatch.setattr(
        rnsh_mod.shutil, "which", lambda _name: "/home/user/.local/bin/rnsh"
    )

    manager = MagicMock()
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {"mode": "connect", "destination": "deadbeef"},
    )
    command = session._build_command()
    assert command[:3] == [rnsh_mod.sys.executable, "-m", rnsh_mod._RNSH_MODULE]
    assert command[-1] == "deadbeef"


def test_rnsh_frozen_uses_meshchatx_run_module(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: True)
    monkeypatch.setattr(rnsh_mod.RNSHSession, "_is_frozen_executable", lambda: True)
    monkeypatch.setattr(rnsh_mod.sys, "executable", r"C:\App\ReticulumMeshChatX.exe")

    manager = MagicMock()
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {"mode": "connect", "destination": "deadbeef"},
    )
    command = session._build_command()
    assert command[:3] == [
        r"C:\App\ReticulumMeshChatX.exe",
        rnsh_mod._MESHCHATX_RUN_MODULE_FLAG,
        rnsh_mod._RNSH_MODULE,
    ]
    assert "-m" not in command
    assert command[-1] == "deadbeef"


def test_rnsh_frozen_listen_command_keeps_mirror_flag_separate(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: True)
    monkeypatch.setattr(rnsh_mod.RNSHSession, "_is_frozen_executable", lambda: True)
    monkeypatch.setattr(rnsh_mod.sys, "executable", "/opt/ReticulumMeshChatX")

    manager = MagicMock()
    manager.reticulum_config_dir = "/tmp/rns-config"
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {
            "mode": "listen",
            "mirror": True,
            "no_auth": True,
            "quiet": 1,
            "config_path": "/tmp/session-config",
        },
    )
    command = session._build_command()
    assert command[:3] == [
        "/opt/ReticulumMeshChatX",
        rnsh_mod._MESHCHATX_RUN_MODULE_FLAG,
        rnsh_mod._RNSH_MODULE,
    ]
    assert command.count("-m") == 1
    assert command.index("-m") > command.index(rnsh_mod._RNSH_MODULE)
    assert "-c" in command
    assert command[command.index("-c") + 1] == "/tmp/session-config"
    assert "-l" in command
    assert "-n" in command
    assert "-q" in command


def test_rnsh_connect_command_includes_destination_and_remote(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: True)
    monkeypatch.setattr(rnsh_mod.RNSHSession, "_is_frozen_executable", lambda: False)

    manager = MagicMock()
    manager.reticulum_config_dir = "/shared/rns"
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {
            "mode": "connect",
            "destination": "aabbccddeeff0011",
            "remote_command": "uname -a",
            "no_id": True,
        },
    )
    command = session._build_command()
    assert command[:3] == [rnsh_mod.sys.executable, "-m", rnsh_mod._RNSH_MODULE]
    assert "-c" in command
    assert command[command.index("-c") + 1] == "/shared/rns"
    assert "-N" in command
    assert "aabbccddeeff0011" in command
    assert "--" in command
    assert command[command.index("--") + 1 :] == ["uname", "-a"]


def test_rnsh_falls_back_to_path_binary_when_module_missing(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: False)
    monkeypatch.setattr(rnsh_mod.shutil, "which", lambda _name: "/usr/bin/rnsh")
    monkeypatch.setattr(rnsh_mod.os, "access", lambda _path, _mode: True)

    manager = MagicMock()
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {"mode": "connect", "destination": "deadbeef"},
    )
    command = session._build_command()
    assert command[0] == "/usr/bin/rnsh"
    assert command[-1] == "deadbeef"


def test_rnsh_non_executable_path_wrapper_raises_permission_error(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: False)
    monkeypatch.setattr(
        rnsh_mod.shutil,
        "which",
        lambda _name: "/home/user/.local/bin/rnsh",
    )
    monkeypatch.setattr(rnsh_mod.os, "access", lambda _path, _mode: False)

    manager = MagicMock()
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {"mode": "connect", "destination": "deadbeef"},
    )
    with pytest.raises(PermissionError, match="Permission denied"):
        session._build_command()


def test_rnsh_missing_module_and_binary_raises_file_not_found(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    monkeypatch.setattr(rnsh_mod.RNSHSession, "_rnsh_module_available", lambda: False)
    monkeypatch.setattr(rnsh_mod.shutil, "which", lambda _name: None)

    manager = MagicMock()
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {"mode": "connect", "destination": "deadbeef"},
    )
    with pytest.raises(FileNotFoundError, match="rnsh is not available"):
        session._build_command()


@pytest.mark.asyncio
async def test_rnsh_session_not_found_returns_404(mock_app):
    mock_app.rnsh_manager = _DummyManager()
    handler = _find_handler(
        mock_app, "/api/v1/rnsh/sessions/{session_id}/start", "POST"
    )
    assert handler is not None
    response = await handler(_make_request(match_info={"session_id": "missing"}))
    assert response.status == 404


@pytest.mark.asyncio
async def test_rnsh_autostart_failure_removes_orphan_session(mock_app):
    manager = _DummyManager()

    def _create_failing(payload):
        manager.created_payload = payload
        session = _DummySession("orphan", start_error=ValueError("bad destination"))
        manager._sessions[session.session_id] = session
        return session

    manager.create_session = _create_failing
    mock_app.rnsh_manager = manager
    handler = _find_handler(mock_app, "/api/v1/rnsh/sessions", "POST")
    assert handler is not None
    response = await handler(
        _make_request(
            json_body={
                "mode": "connect",
                "destination": "",
                "autostart": True,
            },
        ),
    )
    assert response.status == 400
    assert "orphan" in manager.removed_ids
    assert "orphan" not in manager._sessions


def test_rnsh_listen_address_detection_notifies_session_change():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    session.append_output(
        "[Notice] rnsh listening for commands on <8d7f90d560627da94a312bb96ba5c485>\n",
    )
    assert session.listen_address == "8d7f90d560627da94a312bb96ba5c485"
    manager._on_session_change.assert_called()


def test_rnsh_clear_output_resets_output_seq():
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    session.append_output("one")
    session.append_output("two")
    assert session._output_seq == 2
    session.clear_output()
    assert session._output_seq == 0
    assert session.output_since(0) == {"chunks": [], "next_cursor": 0}


def test_rnsh_stop_returns_stopped_status(monkeypatch):
    from meshchatx.src.backend.rnsh_manager import RNSHSession

    class FakeProc:
        def __init__(self):
            self.pid = 42
            self._alive = True
            self.returncode = None

        def poll(self):
            return None if self._alive else self.returncode

        def terminate(self):
            self._alive = False
            self.returncode = 0

        def kill(self):
            self._alive = False
            self.returncode = -9

        def wait(self, timeout=None):
            self._alive = False
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    proc = FakeProc()
    session._process = proc
    session.pid = proc.pid
    session.status = RNSHSession.STATUS_RUNNING

    payload = session.stop()
    assert payload["status"] == RNSHSession.STATUS_STOPPED
    assert payload["pid"] is None
    assert session.status == RNSHSession.STATUS_STOPPED


def test_rnsh_waiter_does_not_clobber_restarted_process():
    import threading
    import time

    from meshchatx.src.backend.rnsh_manager import RNSHSession

    class FakeProc:
        def __init__(self, delay=0.2):
            self.pid = id(self) % 100000
            self._delay = delay
            self._alive = True
            self.returncode = None

        def poll(self):
            return None if self._alive else self.returncode

        def wait(self, timeout=None):
            time.sleep(self._delay)
            self._alive = False
            self.returncode = 0
            return 0

    manager = MagicMock()
    session = RNSHSession(manager, "s1", {"mode": "listen"})
    old = FakeProc(delay=0.25)
    session._process = old
    session.pid = old.pid
    session.status = RNSHSession.STATUS_RUNNING

    waiter = threading.Thread(target=session._waiter_loop, args=(old,), daemon=True)
    waiter.start()
    time.sleep(0.05)

    new = FakeProc(delay=30)
    with session._lock:
        session._process = new
        session.pid = new.pid
        session.status = RNSHSession.STATUS_RUNNING
        session._stop_requested = False

    waiter.join(timeout=2)
    assert session.status == RNSHSession.STATUS_RUNNING
    assert session._process is new
    assert session.pid == new.pid
    assert new.poll() is None


def test_rnsh_start_failure_sets_failed_status(monkeypatch):
    from meshchatx.src.backend import rnsh_manager as rnsh_mod

    manager = MagicMock()
    session = rnsh_mod.RNSHSession(
        manager,
        "s1",
        {"mode": "connect", "destination": "aabbccddeeff0011"},
    )
    monkeypatch.setattr(
        rnsh_mod.RNSHSession,
        "_supports_pty",
        staticmethod(lambda: False),
    )
    monkeypatch.setattr(
        rnsh_mod.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")),
    )
    with pytest.raises(OSError, match="boom"):
        session.start()
    assert session.status == rnsh_mod.RNSHSession.STATUS_FAILED
    assert session.last_error == "boom"
    assert session.pid is None


def test_rnsh_manager_save_is_atomic(tmp_path):
    from meshchatx.src.backend.rnsh_manager import RNSHManager

    manager = RNSHManager(str(tmp_path))
    manager.create_session({"mode": "listen", "name": "atomic"})
    store = tmp_path / "rnsh_sessions.json"
    assert store.exists()
    assert not (tmp_path / "rnsh_sessions.json.tmp").exists()
    data = json.loads(store.read_text(encoding="utf-8"))
    assert len(data["sessions"]) == 1
