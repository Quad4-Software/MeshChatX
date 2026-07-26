# SPDX-License-Identifier: 0BSD

"""Helpers for Landlock integration probes (always run in a subprocess)."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from meshchatx.src.backend.landlock_sandbox import landlock_kernel_supported

REPO_ROOT = Path(__file__).resolve().parents[2]

APPLY_FAILED_MARKER = "APPLY_FAILED"


def landlock_integration_available() -> bool:
    return sys.platform == "linux" and landlock_kernel_supported()


requires_landlock_integration = pytest.mark.skipif(
    not landlock_integration_available(),
    reason="Landlock apply requires a supported Linux kernel",
)


def run_python_under_landlock(
    body: str,
    *,
    storage: str | Path,
    reticulum_config_dir: str | Path | None = None,
    extra_env: dict[str, str] | None = None,
    timeout: float = 90,
) -> subprocess.CompletedProcess[str]:
    """Execute body in a fresh Python process after apply_landlock_sandbox."""
    storage_s = str(storage)
    rns_s = str(reticulum_config_dir) if reticulum_config_dir is not None else None
    rns_kw = f", reticulum_config_dir={rns_s!r}" if rns_s is not None else ""
    body_clean = textwrap.dedent(body).strip()
    script = (
        "import os\n"
        "import sys\n"
        'os.environ["MESHCHAT_LANDLOCK"] = "1"\n'
        "from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox\n"
        f"storage = {storage_s!r}\n"
        "ok = apply_landlock_sandbox(\n"
        f"    storage_dir=storage,\n"
        f"    log_dir=storage{rns_kw},\n"
        ")\n"
        "if not ok:\n"
        f"    print({APPLY_FAILED_MARKER!r})\n"
        "    sys.exit(2)\n"
        f"{body_clean}\n"
    )
    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
        stdin=subprocess.DEVNULL,
    )


def skip_if_landlock_not_applied(result: subprocess.CompletedProcess[str]) -> None:
    if APPLY_FAILED_MARKER in (result.stdout or ""):
        pytest.skip("Landlock could not be applied in this environment")


def assert_probe_ok(
    result: subprocess.CompletedProcess[str],
    *,
    ok_marker: str = "OK",
) -> None:
    skip_if_landlock_not_applied(result)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert ok_marker in (result.stdout or "")
