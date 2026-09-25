# SPDX-License-Identifier: 0BSD

"""Redirect backend test filesystem writes to ./temp-tests/ under the repo root."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_TEMP_ROOT = REPO_ROOT / "temp-tests"
TEST_WORK_DIR = TEST_TEMP_ROOT / "work"
TEST_LOG_DIR = TEST_TEMP_ROOT / "logs"
TEST_COVERAGE_DIR = TEST_TEMP_ROOT / "coverage"
PYTEST_BASE_TEMP = TEST_TEMP_ROOT / "pytest"


RUN_MARKER_PREFIX = ".run-"


def is_xdist_worker() -> bool:
    return os.environ.get("PYTEST_XDIST_WORKER") is not None


def should_reset_test_temp_root() -> bool:
    if os.environ.get("MESHCHAT_TEST_KEEP_TEMP") == "1":
        return False
    return not is_xdist_worker()


def _marker_path() -> Path:
    return TEST_TEMP_ROOT / f"{RUN_MARKER_PREFIX}{os.getpid()}"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _live_markers() -> list[Path]:
    markers = []
    for m in TEST_TEMP_ROOT.glob(f"{RUN_MARKER_PREFIX}*"):
        try:
            pid = int(m.name[len(RUN_MARKER_PREFIX) :])
        except ValueError:
            continue
        if _pid_alive(pid):
            markers.append(m)
        else:
            m.unlink(missing_ok=True)
    return markers


def claim_run_marker() -> None:
    TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    _marker_path().touch()


def reset_test_temp_root() -> None:
    if not should_reset_test_temp_root():
        return
    if not TEST_TEMP_ROOT.exists():
        return
    # Another suite holds a live marker; wiping the shared root mid-run
    # deletes its basetemp and coverage files. Skip the reset instead.
    if any(m != _marker_path() for m in _live_markers()):
        return
    shutil.rmtree(TEST_TEMP_ROOT, ignore_errors=True)


def ensure_test_temp_dirs() -> Path:
    for path in (
        TEST_TEMP_ROOT,
        TEST_WORK_DIR,
        TEST_LOG_DIR,
        TEST_COVERAGE_DIR,
        PYTEST_BASE_TEMP,
    ):
        path.mkdir(parents=True, exist_ok=True)

    work_dir = str(TEST_WORK_DIR)
    os.environ["TMPDIR"] = work_dir
    os.environ["TEMP"] = work_dir
    os.environ["TMP"] = work_dir
    os.environ["MESHCHAT_LOG_DIR"] = str(TEST_LOG_DIR)
    os.environ.setdefault("MESHCHAT_COVERAGE_DIR", str(TEST_COVERAGE_DIR))
    os.environ.setdefault("COVERAGE_FILE", str(TEST_COVERAGE_DIR / ".coverage"))
    return TEST_TEMP_ROOT


def configure_test_temp_environment() -> Path:
    claim_run_marker()
    reset_test_temp_root()
    root = ensure_test_temp_dirs()
    claim_run_marker()
    return root


def subprocess_test_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    ensure_test_temp_dirs()
    env = os.environ.copy()
    if extra:
        env.update(extra)
    return env


def _install_test_env() -> None:
    os.environ.setdefault("MESHCHAT_SKIP_STORAGE_LOCK", "1")
    os.environ.setdefault("MESHCHAT_DISABLE_CSRF", "1")
    configure_test_temp_environment()


_install_test_env()
