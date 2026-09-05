# SPDX-License-Identifier: 0BSD

"""Unit tests for Windows AppContainer sandbox helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend import appcontainer_launcher as launcher
from meshchatx.src.backend.appcontainer_sandbox import core as ac


@pytest.fixture(autouse=True)
def _reset_support_cache():
    ac._appcontainer_support_cached = None
    yield
    ac._appcontainer_support_cached = None


def test_appcontainer_supported_false_on_non_windows():
    with patch.object(ac, "sys") as mock_sys:
        mock_sys.platform = "linux"
        assert ac.appcontainer_supported() is False
        assert ac.appcontainer_requested() is False


def test_appcontainer_disabled_by_env(monkeypatch):
    monkeypatch.setenv("MESHCHAT_APPCONTAINER", "0")
    with patch.object(ac, "sys") as mock_sys:
        mock_sys.platform = "win32"
        assert ac.appcontainer_requested() is False
        assert ac.appcontainer_disabled_by_env() is True
        assert ac.appcontainer_forced() is False


def test_appcontainer_forced_env(monkeypatch):
    monkeypatch.setenv("MESHCHAT_APPCONTAINER", "1")
    with patch.object(ac, "sys") as mock_sys:
        mock_sys.platform = "win32"
        assert ac.appcontainer_requested() is True
        assert ac.appcontainer_auto_enabled() is False
        assert ac.appcontainer_forced() is True


def test_appcontainer_off_by_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("MESHCHAT_APPCONTAINER", raising=False)
    with (
        patch.object(ac, "sys") as mock_sys,
        patch.object(ac, "appcontainer_supported", return_value=True),
    ):
        mock_sys.platform = "win32"
        assert ac.appcontainer_requested() is False
        assert ac.appcontainer_auto_enabled() is False


def test_is_appcontainer_child(monkeypatch):
    monkeypatch.delenv(ac.CHILD_ENV_FLAG, raising=False)
    assert ac.is_appcontainer_child() is False
    monkeypatch.setenv(ac.CHILD_ENV_FLAG, "1")
    assert ac.is_appcontainer_child() is True


def test_collect_rw_roots_includes_storage_and_temp(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    reticulum = tmp_path / "reticulum"
    logs = storage / "logs"
    storage.mkdir()
    reticulum.mkdir()
    logs.mkdir()
    fake_temp = tmp_path / "tmp"
    fake_temp.mkdir()
    monkeypatch.setattr(ac.tempfile, "gettempdir", lambda: str(fake_temp))
    monkeypatch.setattr(ac, "collect_user_exchange_roots", lambda create=True: [])
    roots = ac.collect_rw_roots(str(storage), str(reticulum), str(logs))
    assert str(storage) in roots
    assert str(reticulum) in roots
    assert str(logs) in roots
    assert str(fake_temp) in roots


def test_collect_user_exchange_roots_creates_meshchatx_subdirs(tmp_path, monkeypatch):
    documents = tmp_path / "Documents"
    downloads = tmp_path / "Downloads"
    pictures = tmp_path / "Pictures"
    documents.mkdir()
    downloads.mkdir()
    pictures.mkdir()
    monkeypatch.setattr(ac, "_user_profile_dir", lambda: str(tmp_path))
    monkeypatch.setattr(ac, "_windows_known_folder", lambda _fid: None)
    roots = ac.collect_user_exchange_roots(create=True)
    assert str(documents / "MeshChatX") in roots
    assert str(downloads / "MeshChatX") in roots
    assert str(pictures / "MeshChatX") in roots
    assert (documents / "MeshChatX").is_dir()
    assert (downloads / "MeshChatX").is_dir()
    assert (pictures / "MeshChatX").is_dir()


def test_collect_rw_roots_includes_exchange_dirs(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()
    exchange = tmp_path / "Downloads" / "MeshChatX"
    monkeypatch.setattr(ac.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    monkeypatch.setattr(
        ac,
        "collect_user_exchange_roots",
        lambda create=True: [str(exchange)],
    )
    exchange.mkdir(parents=True)
    roots = ac.collect_rw_roots(str(storage), str(storage), str(storage / "logs"))
    assert str(exchange) in roots
    assert str(tmp_path / "Downloads") not in roots


def test_collect_ro_roots_includes_exe_dir(tmp_path):
    exe_dir = tmp_path / "backend"
    exe_dir.mkdir()
    roots = ac.collect_ro_roots(exe_dir=str(exe_dir))
    assert str(exe_dir) in roots


def test_build_command_line_quotes_spaces():
    line = ac._build_command_line(
        r"C:\Program Files\app.exe",
        ["--storage-dir", r"C:\Users\a b\data"],
    )
    assert '"C:\\Program Files\\app.exe"' in line
    assert '"C:\\Users\\a b\\data"' in line


def test_launcher_rejects_non_windows(monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "linux")
    code = launcher.run_launcher(["--headless", "--port", "9337"])
    assert code == 2


def test_launcher_rejects_nested_child(monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(launcher, "is_appcontainer_child", lambda: True)
    code = launcher.run_launcher(["--headless"])
    assert code == 2


def test_launcher_forced_fails_when_unsupported(monkeypatch):
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(launcher, "is_appcontainer_child", lambda: False)
    monkeypatch.setattr(launcher, "appcontainer_supported", lambda: False)
    monkeypatch.setattr(launcher, "appcontainer_forced", lambda: True)
    code = launcher.run_launcher(["--headless"])
    assert code == 2


def test_launcher_success_path(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(
        launcher.sys,
        "executable",
        str(tmp_path / "ReticulumMeshChatX.exe"),
    )
    monkeypatch.setattr(launcher, "is_appcontainer_child", lambda: False)
    monkeypatch.setattr(launcher, "appcontainer_supported", lambda: True)
    monkeypatch.setattr(launcher, "appcontainer_forced", lambda: False)

    def fake_launch(exe, args, **kwargs):
        assert exe.endswith("ReticulumMeshChatX.exe")
        assert "--headless" in args
        return ac.LaunchResult(ok=True, exit_code=0, used_appcontainer=True)

    monkeypatch.setattr(launcher, "launch_backend_sandboxed", fake_launch)
    code = launcher.run_launcher(
        ["--headless", "--port", "9337", "--storage-dir", str(tmp_path)],
    )
    assert code == 0


def test_main_skips_appcontainer_wrap_for_self_check(monkeypatch, tmp_path):
    """One-shot --self-check must not CreateProcess into an AppContainer."""
    from meshchatx import meshchat as meshchat_mod
    from meshchatx.src.backend.self_check import SELF_CHECK_LABELS

    called = {"launcher": False}

    def boom_launcher(_argv):
        called["launcher"] = True
        return 2

    monkeypatch.setattr(meshchat_mod.sys, "platform", "win32")
    monkeypatch.setattr(meshchat_mod, "appcontainer_requested", lambda: True)
    monkeypatch.setattr(meshchat_mod, "is_appcontainer_child", lambda: False)
    monkeypatch.setattr(
        "meshchatx.src.backend.appcontainer_launcher.run_launcher",
        boom_launcher,
    )
    monkeypatch.setattr(
        meshchat_mod.sys,
        "argv",
        ["meshchat.py", "--storage-dir", str(tmp_path), "--self-check", "--headless"],
    )

    mock_results = {key: {"status": "ok", "reason": ""} for key in SELF_CHECK_LABELS}

    with (
        patch("meshchatx.meshchat.ReticulumMeshChat") as mock_app_class,
        patch("meshchatx.src.backend.identity_context.core.Database"),
        patch("meshchatx.src.backend.identity_context.core.ConfigManager"),
        patch("aiohttp.web.run_app"),
        patch.object(meshchat_mod, "_maybe_run_embedded_module", return_value=False),
    ):
        mock_app_instance = mock_app_class.return_value
        mock_app_instance.run_self_test = MagicMock(return_value=mock_results)
        with pytest.raises(SystemExit) as excinfo:
            meshchat_mod.main()
        assert excinfo.value.code == 0
        assert called["launcher"] is False
        mock_app_instance.run_self_test.assert_called_once()


def test_launcher_reports_launch_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(
        launcher.sys,
        "executable",
        str(tmp_path / "ReticulumMeshChatX.exe"),
    )
    monkeypatch.setattr(launcher, "is_appcontainer_child", lambda: False)
    monkeypatch.setattr(launcher, "appcontainer_supported", lambda: True)
    monkeypatch.setattr(launcher, "appcontainer_forced", lambda: True)
    monkeypatch.setattr(
        launcher,
        "launch_backend_sandboxed",
        lambda *a, **k: ac.LaunchResult(ok=False, error="boom"),
    )
    code = launcher.run_launcher(["--headless"])
    assert code == 1


def test_apply_mitigations_noop_outside_child(monkeypatch):
    monkeypatch.setattr(ac, "is_appcontainer_child", lambda: False)
    with patch.object(ac, "sys") as mock_sys:
        mock_sys.platform = "win32"
        assert ac.apply_windows_process_mitigations() is False


def test_launch_backend_forced_no_fallback(monkeypatch, tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()

    monkeypatch.setattr(ac, "ensure_appcontainer_profile", lambda: object())
    monkeypatch.setattr(ac, "grant_path_access", lambda *a, **k: None)
    monkeypatch.setattr(ac, "revoke_path_access", lambda *a, **k: None)
    monkeypatch.setattr(
        ac,
        "create_process_in_appcontainer",
        lambda *a, **k: (_ for _ in ()).throw(OSError("create failed")),
    )
    monkeypatch.setattr(ac, "collect_ro_roots", lambda **k: [])

    result = ac.launch_backend_sandboxed(
        str(tmp_path / "exe"),
        ["--headless"],
        storage_dir=str(storage),
        reticulum_config_dir=str(storage),
        log_dir=str(storage / "logs"),
        forced=True,
    )
    assert result.ok is False
    assert result.fell_back is False
    assert "create failed" in (result.error or "")


def test_launch_backend_auto_fallback(monkeypatch, tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    sid = object()

    monkeypatch.setattr(ac, "ensure_appcontainer_profile", lambda: sid)
    monkeypatch.setattr(ac, "grant_path_access", lambda *a, **k: None)
    monkeypatch.setattr(ac, "revoke_path_access", lambda *a, **k: None)
    monkeypatch.setattr(
        ac,
        "create_process_in_appcontainer",
        lambda *a, **k: (_ for _ in ()).throw(OSError("create failed")),
    )
    monkeypatch.setattr(
        ac,
        "create_process_unsandboxed",
        lambda *a, **k: (1, 2, 99),
    )
    monkeypatch.setattr(ac, "close_handle", lambda *a, **k: None)
    monkeypatch.setattr(ac, "_wait_process", lambda *a, **k: 0)
    monkeypatch.setattr(ac, "collect_ro_roots", lambda **k: [])

    result = ac.launch_backend_sandboxed(
        str(tmp_path / "exe"),
        ["--headless"],
        storage_dir=str(storage),
        reticulum_config_dir=str(storage),
        log_dir=str(storage / "logs"),
        forced=False,
    )
    assert result.ok is True
    assert result.fell_back is True
    assert result.used_appcontainer is False
    assert result.exit_code == 0
