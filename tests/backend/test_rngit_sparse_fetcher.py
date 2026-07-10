# SPDX-License-Identifier: 0BSD

from pathlib import Path

import pytest

from meshchatx.src.backend.rngit_sparse_fetcher import (
    RngitFetchError,
    RngitSparseFetcher,
    tools_available,
)


def test_tools_available_missing_git():
    ok, code = tools_available(which=lambda name: None)
    assert ok is False
    assert code == "git_missing"


def test_tools_available_missing_remote_helper():
    def which(name):
        if name == "git":
            return "/usr/bin/git"
        return None

    ok, code = tools_available(which=which)
    assert ok is False
    assert code == "git_remote_rns_missing"


@pytest.mark.asyncio
async def test_fetcher_requires_tools(tmp_path):
    fetcher = RngitSparseFetcher(
        work_root=str(tmp_path / "work"),
        reticulum_config_dir=None,
        which=lambda _n: None,
    )
    with pytest.raises(RngitFetchError) as exc:
        await fetcher.fetch(
            destination_hash="a" * 32,
            group="g",
            repository="r",
            paths=["a.geojson"],
            ref="HEAD",
            job_id="job1",
            timeout_seconds=5,
        )
    assert exc.value.code == "rngit_tools_unavailable"


@pytest.mark.asyncio
async def test_fetcher_cleanup_workdir_on_failure(tmp_path, monkeypatch):
    work_root = tmp_path / "work"
    work_root.mkdir()

    async def fake_run_git(args, *, cwd, env, timeout, processes):
        raise RngitFetchError("git_clone_failed", "boom")

    monkeypatch.setattr(
        "meshchatx.src.backend.rngit_sparse_fetcher._run_git",
        fake_run_git,
    )
    fetcher = RngitSparseFetcher(
        work_root=str(work_root),
        reticulum_config_dir=None,
        which=lambda n: f"/bin/{n}",
    )
    with pytest.raises(RngitFetchError):
        await fetcher.fetch(
            destination_hash="a" * 32,
            group="g",
            repository="r",
            paths=["a.geojson"],
            ref="HEAD",
            job_id="jobx",
            timeout_seconds=5,
        )
    assert not (work_root / "jobx").exists()


@pytest.mark.asyncio
async def test_fetcher_reads_sparse_files(tmp_path, monkeypatch):
    work_root = tmp_path / "work"
    work_root.mkdir()
    calls = []

    async def fake_run_git(args, *, cwd, env, timeout, processes):
        calls.append(args)
        if args[:2] == ["git", "clone"]:
            dest = Path(args[-1])
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "maps").mkdir(exist_ok=True)
            (dest / "maps" / "layer.geojson").write_bytes(
                b'{"type":"Point","coordinates":[0,0]}',
            )
            return 0, b"", b""
        if "sparse-checkout" in args:
            return 0, b"", b""
        if "fetch" in args:
            return 0, b"", b""
        if "checkout" in args:
            return 0, b"", b""
        if "rev-parse" in args:
            return 0, b"abc123\n", b""
        return 1, b"", b"unknown"

    monkeypatch.setattr(
        "meshchatx.src.backend.rngit_sparse_fetcher._run_git",
        fake_run_git,
    )
    fetcher = RngitSparseFetcher(
        work_root=str(work_root),
        reticulum_config_dir="/tmp/rns",
        which=lambda n: f"/bin/{n}",
    )
    result = await fetcher.fetch(
        destination_hash="a" * 32,
        group="g",
        repository="r",
        paths=["maps/layer.geojson"],
        ref="main",
        job_id="jobok",
        timeout_seconds=30,
    )
    assert result.resolved_ref == "abc123"
    assert b"Point" in result.files["maps/layer.geojson"]
    assert any("sparse-checkout" in c for c in calls)
    assert not (work_root / "jobok").exists()
