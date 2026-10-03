# SPDX-License-Identifier: 0BSD
"""Schemathesis property-based fuzzing of the live HTTP API.

Spawns a real backend on loopback, fetches a CSRF token so writes are
allowed, and runs schemathesis against docs/openapi.yaml. Every request
stays on 127.0.0.1.

Runs only when MESHCHAT_LIVE_RETICULUM=1.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "e2e"),
)
import backend_harness as bh

pytestmark = pytest.mark.skipif(
    os.environ.get("MESHCHAT_LIVE_RETICULUM") != "1",
    reason="Set MESHCHAT_LIVE_RETICULUM=1 for schemathesis",
)

SPEC = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "openapi.yaml")
TIMEOUT = int(os.environ.get("MESHCHAT_SCHEMATHESIS_SECONDS", "120"))


@pytest.fixture
def backend(tmp_path):
    tmp = str(tmp_path)
    port = bh.free_port()
    bh.write_rns_config(tmp)
    proc, log = bh.spawn_backend(tmp, port)
    try:
        assert bh.wait_ready(port, timeout_s=180), "backend never became ready"
        yield port, tmp
    finally:
        bh.kill_proc(proc)
        log.close()


def test_openapi_fuzz_loopback(backend):
    port, _tmp = backend
    # Grab session + CSRF so schemathesis can exercise write endpoints too.
    jar = {}
    try:
        bh.request(port, "/api/v1/auth/csrf", jar=jar, timeout=10)
    except Exception:
        pass
    headers = []
    if jar.get("cookie"):
        headers += ["-H", f"Cookie: {jar['cookie']}"]
    if jar.get("csrf"):
        headers += ["-H", f"X-CSRF-Token: {jar['csrf']}"]

    env = dict(os.environ)
    proc = subprocess.run(
        [
            "schemathesis",
            "run",
            os.path.abspath(SPEC),
            "--url",
            f"http://127.0.0.1:{port}",
            "--max-time",
            str(TIMEOUT),
            "--phases",
            "examples,coverage",
            "--suppress-health-check",
            "too_slow,filter_too_much",
            "--checks",
            # Gate on the serious checks only: 5xx crashes and responses
            # that break the declared contract. negative_data_rejection
            # flags endpoints that leniently accept malformed bodies. the
            # app tolerates those by design so they stay off until each
            # is triaged (they produce findings, not crashes).
            "not_a_server_error,status_code_conformance,response_schema_conformance",
            "--workers",
            "4",
            *headers,
        ],
        cwd=bh.ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT + 120,
    )
    tail = (proc.stdout + proc.stderr)[-4000:]
    # A 5xx-detecting check counts as a finding. other statuses are
    # information Schemathesis reports in its summary.
    assert proc.returncode == 0 or "SUMMARY" not in tail, tail
    assert proc.returncode == 0, f"schemathesis failed:\n{tail}"


def test_openapi_spec_valid():
    import yaml

    with open(SPEC) as f:
        doc = yaml.safe_load(f)
    assert doc["openapi"].startswith("3.")
    assert len(doc.get("paths", {})) >= 20
    # Every operation needs a declared response.
    for path, item in doc["paths"].items():
        for method, op in item.items():
            if method.startswith("x-") or method == "parameters":
                continue
            assert op.get("responses"), f"{method.upper()} {path} has no responses"
