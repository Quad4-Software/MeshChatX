"""Smoke checks for packaging and docker assets."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "rel",
    [
        "packaging/systemd/rns-filesync.service",
        "packaging/systemd/rns-filesync.user.service",
        "packaging/openrc/rns-filesync",
        "packaging/dinit/rns-filesync",
        "packaging/runit/rns-filesync/run",
        "packaging/sysusers.d/rns-filesync.conf",
        "packaging/tmpfiles.d/rns-filesync.conf",
        "docker/Dockerfile",
        "docker/Dockerfile.build",
        "docker/README.md",
    ],
)
def test_packaging_and_docker_files_exist(rel):
    path = ROOT / rel
    assert path.is_file(), rel


def test_systemd_unit_is_non_root_and_hardened():
    text = (ROOT / "packaging/systemd/rns-filesync.service").read_text(encoding="utf-8")
    assert "User=rns-filesync" in text
    assert "NoNewPrivileges=true" in text
    assert "ProtectSystem=strict" in text
    assert "--no-repl" in text
    assert "User=root" not in text


def test_dockerfile_is_rootless_multistage():
    text = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert "AS builder" in text
    assert "AS runtime" in text
    assert "USER filesync" in text
    assert "adduser" in text
    assert "USER root" not in text.split("AS runtime", 1)[-1]
