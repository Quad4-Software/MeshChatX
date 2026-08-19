# SPDX-License-Identifier: 0BSD

"""Sparse fetch of specific files from an RNGit rns:// repository."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from meshchatx.src.backend.map_overlay_sources import is_commit_like_ref
from meshchatx.src.path_utils import is_path_within_dir

_JOB_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RngitFetchError(RuntimeError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


@dataclass
class RngitFetchResult:
    files: dict[str, bytes]
    resolved_ref: str


def tools_available(
    *,
    which: Callable[[str], str | None] | None = None,
) -> tuple[bool, str | None]:
    finder = which or shutil.which
    if not finder("git"):
        return False, "git_missing"
    if not finder("git-remote-rns"):
        return False, "git_remote_rns_missing"
    return True, None


async def _run_git(
    args: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    timeout: float,
    processes: list,
) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    processes.append(proc)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError as exc:
        _kill_process_group(proc)
        raise RngitFetchError("git_timeout") from exc
    return proc.returncode or 0, stdout or b"", stderr or b""


def _kill_process_group(proc) -> None:
    try:
        if proc.returncode is None:
            os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class RngitSparseFetcher:
    def __init__(
        self,
        *,
        work_root: str,
        reticulum_config_dir: str | None,
        rngit_config_dir: str | None = None,
        which: Callable[[str], str | None] | None = None,
    ):
        self.work_root = work_root
        self.reticulum_config_dir = reticulum_config_dir
        self.rngit_config_dir = rngit_config_dir
        self._which = which or shutil.which
        self._cancelled = False
        self._processes: list = []

    def cancel(self) -> None:
        self._cancelled = True
        for proc in list(self._processes):
            _kill_process_group(proc)

    def _check_cancelled(self) -> None:
        if self._cancelled:
            raise RngitFetchError("cancelled")

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.reticulum_config_dir:
            env["RNS_CONFIG"] = self.reticulum_config_dir
        if self.rngit_config_dir:
            env["RNGIT_CONFIG"] = self.rngit_config_dir
        return env

    def _job_workdir(self, job_id: str) -> str:
        if not isinstance(job_id, str) or not job_id or "\x00" in job_id:
            raise RngitFetchError("invalid_job_id")
        cleaned = job_id.strip()
        if (
            not cleaned
            or cleaned in (".", "..")
            or ".." in cleaned
            or "/" in cleaned
            or "\\" in cleaned
            or cleaned.startswith(".")
        ):
            raise RngitFetchError("invalid_job_id")
        if not _JOB_ID_RE.fullmatch(cleaned) or cleaned.startswith("."):
            raise RngitFetchError("invalid_job_id")
        os.makedirs(self.work_root, exist_ok=True)
        workdir = os.path.join(self.work_root, cleaned)
        if not is_path_within_dir(workdir, self.work_root):
            raise RngitFetchError("path_traversal")
        return workdir

    async def fetch(
        self,
        *,
        destination_hash: str,
        group: str,
        repository: str,
        paths: list[str],
        ref: str = "HEAD",
        job_id: str,
        timeout_seconds: float = 300.0,
        on_phase: Callable[[str], None] | None = None,
    ) -> RngitFetchResult:
        ok, missing = tools_available(which=self._which)
        if not ok:
            raise RngitFetchError("rngit_tools_unavailable", missing)

        if not paths:
            raise RngitFetchError("missing_paths")

        workdir = self._job_workdir(job_id)
        if os.path.exists(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)

        env = self._build_env()
        remote = f"rns://{destination_hash}/{group}/{repository}"
        deadline_budget = float(timeout_seconds)

        def emit(phase: str) -> None:
            if on_phase:
                try:
                    on_phase(phase)
                except Exception:
                    pass

        try:
            self._check_cancelled()
            emit("cloning")
            code, _out, err = await _run_git(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--sparse",
                    "--no-checkout",
                    remote,
                    workdir,
                ],
                cwd=None,
                env=env,
                timeout=deadline_budget,
                processes=self._processes,
            )
            if code != 0:
                raise RngitFetchError(
                    "git_clone_failed",
                    err.decode("utf-8", errors="replace")[:500],
                )

            self._check_cancelled()
            emit("sparse_checkout")
            code, _out, err = await _run_git(
                ["git", "sparse-checkout", "set", "--no-cone", "--", *paths],
                cwd=workdir,
                env=env,
                timeout=min(60.0, deadline_budget),
                processes=self._processes,
            )
            if code != 0:
                raise RngitFetchError(
                    "sparse_checkout_failed",
                    err.decode("utf-8", errors="replace")[:500],
                )

            self._check_cancelled()
            emit("fetching_ref")
            fetch_ref = ref if ref != "HEAD" else "HEAD"
            if is_commit_like_ref(ref):
                code, _out, err = await _run_git(
                    ["git", "fetch", "--depth", "1", "origin", ref],
                    cwd=workdir,
                    env=env,
                    timeout=deadline_budget,
                    processes=self._processes,
                )
                if code != 0:
                    raise RngitFetchError(
                        "git_fetch_failed",
                        err.decode("utf-8", errors="replace")[:500],
                    )
                checkout_target = "FETCH_HEAD"
            else:
                code, _out, err = await _run_git(
                    ["git", "fetch", "--depth", "1", "origin", fetch_ref],
                    cwd=workdir,
                    env=env,
                    timeout=deadline_budget,
                    processes=self._processes,
                )
                if code != 0 and fetch_ref != "HEAD":
                    raise RngitFetchError(
                        "git_fetch_failed",
                        err.decode("utf-8", errors="replace")[:500],
                    )
                checkout_target = "FETCH_HEAD" if code == 0 else "HEAD"

            self._check_cancelled()
            emit("checking_out")
            code, _out, err = await _run_git(
                ["git", "checkout", checkout_target, "--", *paths],
                cwd=workdir,
                env=env,
                timeout=min(120.0, deadline_budget),
                processes=self._processes,
            )
            if code != 0:
                # Fallback: checkout tree then ensure paths exist
                code2, _out2, err2 = await _run_git(
                    ["git", "checkout", checkout_target],
                    cwd=workdir,
                    env=env,
                    timeout=min(120.0, deadline_budget),
                    processes=self._processes,
                )
                if code2 != 0:
                    raise RngitFetchError(
                        "git_checkout_failed",
                        (err or err2).decode("utf-8", errors="replace")[:500],
                    )

            code, out, err = await _run_git(
                ["git", "rev-parse", "HEAD"],
                cwd=workdir,
                env=env,
                timeout=30.0,
                processes=self._processes,
            )
            if code != 0:
                raise RngitFetchError("rev_parse_failed")
            resolved = out.decode("utf-8", errors="replace").strip()

            files: dict[str, bytes] = {}
            root = Path(workdir).resolve()
            for rel in paths:
                candidate = root / rel
                if candidate.is_symlink():
                    raise RngitFetchError("path_traversal")
                abs_path = candidate.resolve()
                if not is_path_within_dir(str(abs_path), str(root)):
                    raise RngitFetchError("path_traversal")
                if not abs_path.is_file() or abs_path.is_symlink():
                    raise RngitFetchError("path_missing", rel)
                files[rel] = abs_path.read_bytes()

            emit("done")
            return RngitFetchResult(files=files, resolved_ref=resolved)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
            self._processes.clear()
