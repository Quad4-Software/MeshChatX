# SPDX-License-Identifier: 0BSD

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _slow_manifest() -> str:
    proc = subprocess.run(  # nosec: BAN-B607
        ["sh", "scripts/ci/tree-manifest.sh", "generate"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "PATH": __import__("os").environ.get("PATH", ""),
        },
        check=False,
    )
    # Force slow path by temporarily hiding the python helper name is awkward.
    # Compare fast output to a golden re-run via inline shell loop instead.
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _fast_manifest() -> str:
    proc = subprocess.run(  # nosec: BAN-B607
        ["python3", "scripts/ci/tree_manifest_generate.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _legacy_shell_manifest() -> str:
    """Same rules as tree-manifest.sh generate before the Python fast path."""
    header = "# meshchatx tree manifest v1"
    lines = [header]
    env = {"LC_ALL": "C"}
    paths = subprocess.check_output(["git", "ls-files"], cwd=REPO, env=env, text=True)  # nosec: BAN-B607
    for f in sorted(paths.splitlines(), key=lambda s: s):
        if not f:
            continue
        if f == "meshchatx.rsm":
            continue
        if f == "vendor" or f.startswith("vendor/"):
            continue
        if "/vendor/" in f or f.endswith("/vendor"):
            continue
        check = subprocess.run(  # nosec: BAN-B607
            ["git", "cat-file", "-e", f":{f}"],
            cwd=REPO,
            capture_output=True,
        )
        if check.returncode != 0:
            continue
        mode = subprocess.check_output(  # nosec: BAN-B607
            ["git", "ls-files", "-s", "--", f],
            cwd=REPO,
            text=True,
        ).split()[0]
        if mode not in ("100644", "100755"):
            continue
        digest = subprocess.check_output(  # nosec: BAN-B607
            ["sh", "-c", "git show \":$1\" | sha256sum | awk '{print $1}'", "_", f],
            cwd=REPO,
            text=True,
        ).strip()
        lines.append(f"{digest}  {f}")
    return "\n".join(lines) + "\n"


def test_fast_manifest_matches_legacy_shell_algorithm():
    legacy = _legacy_shell_manifest()
    fast = _fast_manifest()
    assert fast == legacy


def test_tree_manifest_sh_uses_fast_generator():
    via_sh = _slow_manifest()
    fast = _fast_manifest()
    assert via_sh == fast
