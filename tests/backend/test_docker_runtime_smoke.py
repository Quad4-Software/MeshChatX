# SPDX-License-Identifier: 0BSD

"""Docker image runtime smoke test (build + /api/v1/status)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SMOKE_SCRIPT = _REPO_ROOT / "scripts" / "ci" / "docker-runtime-smoke.sh"
_HARDENED_SMOKE_SCRIPT = _REPO_ROOT / "scripts" / "ci" / "docker-hardened-smoke.sh"
_DEMO_SMOKE_SCRIPT = _REPO_ROOT / "scripts" / "ci" / "docker-demo-smoke.sh"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(  # nosec: BAN-B607
            ["docker", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("MESHCHAT_DOCKER_SMOKE") != "1",
    reason="Set MESHCHAT_DOCKER_SMOKE=1 to run Docker runtime smoke (build + /api/v1/status)",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker is not available")
def test_docker_image_serves_status():
    env = os.environ.copy()
    env.setdefault("MESHCHAT_DOCKER_SMOKE_TIMEOUT", "240")
    result = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_SMOKE_SCRIPT)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=int(env["MESHCHAT_DOCKER_SMOKE_TIMEOUT"]) + 120,
        check=False,
    )
    assert result.returncode == 0, (
        f"Docker runtime smoke failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert '"status": "ok"' in result.stdout or '"status":"ok"' in result.stdout


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("MESHCHAT_DOCKER_SMOKE") != "1",
    reason="Set MESHCHAT_DOCKER_SMOKE=1 to run Docker hardened compose + run smoke",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker is not available")
def test_docker_hardened_compose_and_run_serve_status():
    env = os.environ.copy()
    env.setdefault("MESHCHAT_DOCKER_SMOKE_TIMEOUT", "240")
    result = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_HARDENED_SMOKE_SCRIPT)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=int(env["MESHCHAT_DOCKER_SMOKE_TIMEOUT"]) + 600,
        check=False,
    )
    assert result.returncode == 0, (
        f"Docker hardened smoke failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert '"status": "ok"' in result.stdout or '"status":"ok"' in result.stdout


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("MESHCHAT_DOCKER_SMOKE") != "1",
    reason="Set MESHCHAT_DOCKER_SMOKE=1 to run Docker demo compose smoke",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker is not available")
def test_docker_demo_compose_smoke():
    env = os.environ.copy()
    env.setdefault("MESHCHAT_DOCKER_SMOKE_TIMEOUT", "240")
    result = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_DEMO_SMOKE_SCRIPT)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=int(env["MESHCHAT_DOCKER_SMOKE_TIMEOUT"]) + 600,
        check=False,
    )
    assert result.returncode == 0, (
        f"Docker demo smoke failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("MESHCHAT_DOCKER_SMOKE") != "1",
    reason="Set MESHCHAT_DOCKER_SMOKE=1 to run Docker runtime smoke",
)
@pytest.mark.skipif(not _docker_available(), reason="Docker is not available")
def test_docker_status_json_shape():
    """Lightweight follow-up: status body matches minimal contract when smoke script left output."""
    sample = {"status": "ok", "listen_port": 8000, "https_enabled": True}
    from tests.backend.api_json_contract_schemas import (
        API_V1_STATUS_SCHEMA,
        assert_matches_schema,
    )

    assert_matches_schema(sample, API_V1_STATUS_SCHEMA)
