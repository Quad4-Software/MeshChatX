# SPDX-License-Identifier: 0BSD

"""Landlock regression probes for subprocess and user-local tool surfaces."""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from meshchatx.src.backend import landlock_sandbox as ll
from tests.backend.landlock_integration_support import (
    assert_probe_ok,
    requires_landlock_integration,
    run_python_under_landlock,
    skip_if_landlock_not_applied,
)


def test_collect_user_local_cli_roots_expected_layout(tmp_path, monkeypatch):
    home = tmp_path / "home"
    local_bin = home / ".local" / "bin"
    pipx = home / ".local" / "share" / "pipx"
    argos = home / ".local" / "share" / "argos-translate"
    local_bin.mkdir(parents=True)
    pipx.mkdir(parents=True)
    argos.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    roots = set(ll._collect_user_local_cli_roots())
    assert str(local_bin) in roots
    assert str(pipx) in roots
    assert str(argos) in roots


def test_collect_rw_roots_includes_argos_share_when_present(tmp_path, monkeypatch):
    home = tmp_path / "home"
    argos = home / ".local" / "share" / "argos-translate"
    argos.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    storage = tmp_path / "storage"
    storage.mkdir()
    rw = ll._collect_rw_roots(str(storage), None, str(storage))
    assert str(argos) in rw


@requires_landlock_integration
def test_landlock_denies_write_directly_under_home(tmp_path):
    """HOME is not an RW root; only storage, temp, and explicit shares are."""
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        """
        import os
        import sys

        path = os.path.join(
            os.path.expanduser("~"),
            ".meshchatx_landlock_write_probe",
        )
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("x")
        except PermissionError:
            print("OK")
            sys.exit(0)
        try:
            os.remove(path)
        except OSError:
            pass
        print("WRITE_SHOULD_HAVE_FAILED")
        sys.exit(3)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_allows_storage_and_temp_writes(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        f"""
        import os
        import sys
        import tempfile

        storage = {str(storage)!r}
        path = os.path.join(storage, "rw-check.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("storage")
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=True,
        ) as tmp:
            tmp.write("temp")
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_child_interpreter_spawn():
    """Same pattern as self_check.check_subprocess_spawn."""
    storage = tempfile.mkdtemp(prefix="meshchat_ll_spawn_")
    result = run_python_under_landlock(
        """
        import subprocess
        import sys

        child = subprocess.run(
            [sys.executable, "-c", "print('meshchatx-spawn-ok', flush=True)"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        if child.returncode != 0:
            print("SPAWN_RC", child.returncode, child.stderr)
            sys.exit(4)
        if "meshchatx-spawn-ok" not in (child.stdout or ""):
            print("SPAWN_BAD_OUT", child.stdout)
            sys.exit(5)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_self_check_subprocess_spawn_helper():
    storage = tempfile.mkdtemp(prefix="meshchat_ll_selfcheck_")
    result = run_python_under_landlock(
        """
        import sys
        from meshchatx.src.backend.self_check import check_subprocess_spawn

        out = check_subprocess_spawn()
        if out.get("status") != "ok":
            print("SELF_CHECK_FAIL", out.get("reason", ""))
            sys.exit(3)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_translator_handler_lists_argos_languages(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        """
        import sys
        from meshchatx.src.backend.translator_handler import TranslatorHandler

        handler = TranslatorHandler(translator_argos_enabled=True)
        if not handler.has_argos:
            print("SKIP_NO_ARGOS")
            sys.exit(0)
        resp = handler.get_translator_languages_response()
        argos = [x for x in resp["languages"] if x.get("source") == "argos"]
        if not argos:
            print("EMPTY_ARGOS_LANGS has_lib", handler.has_argos_lib, "has_cli", handler.has_argos_cli)
            sys.exit(4)
        print("OK", len(argos))
        sys.exit(0)
        """,
        storage=storage,
        timeout=120,
    )
    skip_if_landlock_not_applied(result)
    if "SKIP_NO_ARGOS" in (result.stdout or ""):
        pytest.skip("Argos Translate not installed on this host")
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_argospm_list_when_installed(tmp_path):
    if not shutil.which("argospm"):
        pytest.skip("argospm not on PATH")
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        """
        import subprocess
        import sys

        proc = subprocess.run(
            ["argospm", "list"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            print("ARGOSPM_FAIL", proc.stderr or proc.stdout)
            sys.exit(3)
        if not (proc.stdout or "").strip():
            print("ARGOSPM_EMPTY")
            sys.exit(4)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_argos_translate_cli_when_installed(tmp_path):
    executable = shutil.which("argos-translate")
    if not executable:
        pytest.skip("argos-translate not on PATH")
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        f"""
        import subprocess
        import sys

        proc = subprocess.run(
            [{executable!r}, "--from-lang", "en", "--to-lang", "ru", "hello"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0:
            print("TRANSLATE_FAIL", proc.stderr or proc.stdout)
            sys.exit(3)
        if not (proc.stdout or "").strip():
            print("TRANSLATE_EMPTY")
            sys.exit(4)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
        timeout=180,
    )
    skip_if_landlock_not_applied(result)
    if result.returncode != 0 and "translate-en_ru" in (
        result.stdout or result.stderr or ""
    ):
        pytest.skip("translate-en_ru package not installed")
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_argos_share_allows_stanza_style_temp_dir(tmp_path):
    home = os.path.expanduser("~")
    argos_share = os.path.join(home, ".local", "share", "argos-translate")
    if not os.path.isdir(argos_share):
        pytest.skip("Argos data directory not present")
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        f"""
        import os
        import sys
        import tempfile

        base = {argos_share!r}
        with tempfile.TemporaryDirectory(dir=base) as td:
            path = os.path.join(td, "probe.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("ok")
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_user_local_bin_script_executable(tmp_path):
    local_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
    if not os.path.isdir(local_bin):
        pytest.skip("~/.local/bin not present")
    # Pipx-style CLIs only. git-remote-rns imports RNS at startup and is not a
    # generic --help smoke target for Landlock execute permission.
    preferred = (
        ("argospm", ["--help"]),
        ("argos-translate", ["--help"]),
        ("argostranslate", ["--help"]),
    )
    cmd = None
    cmd_argv = None
    for name, extra_argv in preferred:
        path = os.path.join(local_bin, name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            cmd = path
            cmd_argv = [path, *extra_argv]
            break
    if cmd is None or cmd_argv is None:
        pytest.skip("no known pipx-style CLI in ~/.local/bin")
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        f"""
        import subprocess
        import sys

        proc = subprocess.run(
            {cmd_argv!r},
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode != 0:
            print("EXEC_FAIL", proc.stderr)
            sys.exit(3)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_git_version_when_git_on_path(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("git not on PATH")
    storage = tmp_path / "storage"
    storage.mkdir()
    result = run_python_under_landlock(
        f"""
        import subprocess
        import sys

        proc = subprocess.run(
            [{git!r}, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if proc.returncode != 0:
            print("GIT_FAIL", proc.stderr)
            sys.exit(3)
        if "git version" not in (proc.stdout or ""):
            print("GIT_BAD_OUT", proc.stdout)
            sys.exit(4)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
    )
    assert_probe_ok(result)


@requires_landlock_integration
def test_landlock_rnsh_module_spawn_when_installed(tmp_path):
    try:
        import importlib.util

        if importlib.util.find_spec("RNS.Utilities.rnsh.rnsh") is None:
            pytest.skip("rnsh module not installed")
    except (ImportError, ValueError, AttributeError):
        pytest.skip("rnsh module not installed")

    storage = tmp_path / "storage"
    rns_dir = tmp_path / "rns"
    rns_dir.mkdir()
    storage.mkdir()
    result = run_python_under_landlock(
        """
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, "-m", "RNS.Utilities.rnsh.rnsh", "--help"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode not in (0, 1, 2) and "rnsh" not in out.lower():
            print("RNSH_HELP_FAIL", proc.returncode, out[-500:])
            sys.exit(3)
        print("OK")
        sys.exit(0)
        """,
        storage=storage,
        reticulum_config_dir=rns_dir,
    )
    assert_probe_ok(result)


@pytest.mark.parametrize(
    ("path_name", "collector"),
    [
        ("local_bin", lambda home: os.path.join(home, ".local", "bin")),
        ("pipx", lambda home: os.path.join(home, ".local", "share", "pipx")),
        (
            "argos_share",
            lambda home: os.path.join(home, ".local", "share", "argos-translate"),
        ),
    ],
)
def test_read_roots_cover_user_local_paths_when_present(path_name, collector):
    home = os.path.expanduser("~")
    target = collector(home)
    if not os.path.isdir(target):
        pytest.skip(f"{path_name} not present on this host")
    roots = ll._collect_read_roots()
    assert any(
        target == root or target.startswith(root.rstrip("/") + "/") for root in roots
    ), f"{target!r} not covered by landlock read roots ({path_name})"
