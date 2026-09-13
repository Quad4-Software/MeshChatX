#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
r"""MeshChatX rngit release helper.

Wraps the rngit release manager and the Python artifact builds so a release
is one command instead of a string of shell invocations.

Usage::

    python scripts/rngit_release.py list
    python scripts/rngit_release.py view v4.9.0
    python scripts/rngit_release.py fetch "v4.9.0:manifest.rsm" --dest /tmp/x
    python scripts/rngit_release.py verify /tmp/x/MeshChatX_v4.9.0.rsm
    python scripts/rngit_release.py build
    python scripts/rngit_release.py create v4.9.0 --notes-file notes.md
    python scripts/rngit_release.py delete v4.9.0 --yes
    python scripts/rngit_release.py release v4.9.0 --notes-file notes.md

Anything not covered passes through raw:

    python scripts/rngit_release.py raw perms rns://.../public/MeshChatX

Notes on behaviour:

- rngit is invoked as ``python -m RNS.Utilities.rngit.server`` instead of the
  ``rngit`` wrapper so the client_config editor override is bypassed and this
  script controls $EDITOR. With --notes/--notes-file/--changelog a shim editor
  writes the notes file over rngit's template, which makes create fully
  non-interactive. With --edit the user's own $EDITOR opens instead.
- The release identity defaults to rngit's own (~/.rngit/client_identity);
  override with --identity or RNGIT_IDENTITY. --signer selects a different
  signing identity.
- create signs every file in the artifacts directory and uploads it plus the
  generated .rsg signatures and manifest.rsm. Stale .rsg/manifest.rsm files
  are removed first so they are not shipped as artifacts.
- The artifacts directory convention here is python-dist/: the wheel lands
  there via move_wheels.py and the pyz is built straight into it.

Environment: MESHCHATX_RNGIT_REMOTE, RNGIT_IDENTITY, RNGIT_SIGNER,
RNGIT_RELEASE_NAME, MESHCHATX_RNGIT_ARTIFACTS, PYZ_PYTHON_VERSION.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE = "rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX"
DEFAULT_ARTIFACTS = "python-dist"
RNGIT_MODULE = "RNS.Utilities.rngit.server"


def fail(msg: str, code: int = 1) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def rngit_python() -> str:
    """Return a python executable that can import RNS (and therefore rngit)."""
    candidates = [sys.executable, shutil.which("python3"), shutil.which("python")]
    for cand in candidates:
        if not cand:
            continue
        try:
            subprocess.run(
                [cand, "-c", "import RNS"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return cand
        except (OSError, subprocess.CalledProcessError):
            continue
    fail(
        "no python interpreter with RNS found; install rns or run inside the project venv"
    )


def rngit_argv(args, release_args: list[str]) -> list[str]:
    argv = [rngit_python(), "-m", RNGIT_MODULE, "release"]
    if args.config:
        argv += ["--config", args.config]
    if args.rnsconfig:
        argv += ["--rnsconfig", args.rnsconfig]
    argv += release_args
    argv += ["-v"] * args.verbose + ["-q"] * args.quiet
    return argv


def run_rngit(
    args,
    release_args: list[str],
    *,
    editor: Path | None = None,
    stdin: str | None = None,
    cwd: Path | None = None,
) -> int:
    env = dict(os.environ)
    if editor is not None:
        env["EDITOR"] = str(editor)
    proc = subprocess.run(
        rngit_argv(args, release_args),
        env=env,
        input=stdin,
        text=True,
        cwd=cwd or ROOT,
    )
    return proc.returncode


def remote_of(args) -> str:
    remote = args.remote or os.environ.get("MESHCHATX_RNGIT_REMOTE") or DEFAULT_REMOTE
    if not remote.startswith("rns://"):
        fail(f"remote must be an rns:// URL, got {remote!r}")
    return remote


def artifacts_dir(args) -> Path:
    rel = (
        args.artifacts_dir
        or os.environ.get("MESHCHATX_RNGIT_ARTIFACTS")
        or DEFAULT_ARTIFACTS
    )
    return (ROOT / rel).resolve()


def identity_args(args) -> list[str]:
    out: list[str] = []
    identity = args.identity or os.environ.get("RNGIT_IDENTITY")
    signer = args.signer or os.environ.get("RNGIT_SIGNER")
    name = getattr(args, "name", None) or os.environ.get("RNGIT_RELEASE_NAME")
    if identity:
        out += ["-i", os.path.expanduser(identity)]
    if signer:
        out += ["-s", os.path.expanduser(signer)]
    if name:
        out += ["-n", name]
    return out


def package_version() -> str:
    data = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not re.match(r"^\d+\.\d+\.\d+", version):
        fail("package.json has no usable version field")
    return version


def clean_generated_sidecars(path: Path) -> None:
    """Drop manifest.rsm and *.rsg so rngit regenerates instead of shipping them."""
    for entry in path.iterdir():
        if entry.is_file() and (
            entry.name == f"manifest.{_MSG_EXT}" or entry.name.endswith(f".{_SIG_EXT}")
        ):
            entry.unlink()


_MSG_EXT = "rsm"
_SIG_EXT = "rsg"


def write_editor_shim(notes_text: str) -> Path:
    """Create a temp editor that replaces rngit's notes template with our text."""
    tmpdir = Path(tempfile.mkdtemp(prefix="rngit-release-"))
    notes = tmpdir / "notes.md"
    notes.write_text(notes_text, encoding="utf-8")
    shim = tmpdir / "editor.sh"
    shim.write_text(f'#!/bin/sh\ncat "{notes}" > "$1"\n', encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def changelog_notes(tag: str) -> str:
    """Pull the CHANGELOG section for a tag like v4.9.0 or 4.9.0."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    bare = tag.lstrip("v")
    match = re.search(
        rf"^## \[{re.escape(bare)}\].*?$(.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        fail(f"no changelog section found for {bare}")
    body = match.group(1).strip()
    body = re.sub(r"^### .*$", "", body, flags=re.MULTILINE)
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def resolve_notes(args, tag: str):
    """Return (shim_path or None). None means interactive editing."""
    if args.notes is not None:
        return write_editor_shim(args.notes + "\n")
    if args.notes_file is not None:
        return write_editor_shim(Path(args.notes_file).read_text(encoding="utf-8"))
    if args.changelog:
        return write_editor_shim(changelog_notes(tag) + "\n")
    if args.edit or sys.stdin.isatty():
        return None
    fail(
        "non-interactive create needs --notes, --notes-file or --changelog (or pass --edit)"
    )


def cmd_build(args) -> int:
    out = artifacts_dir(args)
    out.mkdir(parents=True, exist_ok=True)
    if not args.skip_wheel:
        uv = shutil.which("uv") or fail("uv not found on PATH")
        subprocess.run([uv, "build", "--wheel"], cwd=ROOT, check=True)
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "move_wheels.py")],
            cwd=ROOT,
            check=True,
        )
    if not args.skip_pyz:
        bash = shutil.which("bash") or fail("bash not found on PATH")
        version = package_version()
        env = dict(os.environ)
        env["SKIP_WHEEL"] = "1"
        env["PYZ_OUTPUT"] = str(out / f"meshchatx-{version}.pyz")
        subprocess.run(
            [bash, str(ROOT / "scripts" / "build-pyz.sh")],
            cwd=ROOT,
            env=env,
            check=True,
        )
    print(f"artifacts in {out}:")
    for entry in sorted(out.iterdir()):
        print(f"  {entry.name} ({entry.stat().st_size} bytes)")
    return 0


def cmd_create(args, tag: str | None = None) -> int:
    tag = tag or args.tag
    out = artifacts_dir(args)
    if not out.is_dir():
        fail(f"artifacts directory {out} does not exist; run build first")
    if not any(p.is_file() for p in out.iterdir()):
        fail(f"artifacts directory {out} is empty")
    clean_generated_sidecars(out)
    editor = resolve_notes(args, tag)
    extra = identity_args(args)
    if getattr(args, "local", False):
        extra.append("-L")
    extra += [remote_of(args), "create", f"{tag}:{out}"]
    return run_rngit(args, extra, editor=editor)


def cmd_delete(args) -> int:
    extra = [*identity_args(args), remote_of(args), "delete", args.tag]
    stdin = "y\n" if args.yes else None
    return run_rngit(args, extra, stdin=stdin)


def cmd_fetch(args) -> int:
    dest = Path(args.dest).resolve() if args.dest else Path.cwd()
    dest.mkdir(parents=True, exist_ok=True)
    extra = [*identity_args(args), remote_of(args), "fetch", args.target]
    return run_rngit(args, extra, cwd=dest)


def cmd_verify(args) -> int:
    manifest = Path(args.manifest).expanduser().resolve()
    if not manifest.is_file():
        fail(f"manifest {manifest} not found")
    return run_rngit(args, ["-o", str(manifest), "verify"])


def cmd_simple(args, operation: str, target: str | None = None) -> int:
    extra = [*identity_args(args), remote_of(args), operation]
    if target:
        extra.append(target)
    return run_rngit(args, extra)


def cmd_release(args) -> int:
    """Full pipeline: build artifacts, create release, verify it back."""
    rc = cmd_build(args)
    if rc != 0:
        return rc
    rc = cmd_create(args, tag=args.tag)
    if rc != 0:
        return rc
    if args.no_verify:
        return 0
    with tempfile.TemporaryDirectory(prefix="rngit-verify-") as tmp:
        tmpdir = Path(tmp)
        fetch_args = argparse.Namespace(
            **{**vars(args), "target": f"{args.tag}:manifest.{_MSG_EXT}", "dest": tmp}
        )
        rc = cmd_fetch(fetch_args)
        if rc != 0:
            return rc
        manifests = list(tmpdir.glob(f"*.{_MSG_EXT}"))
        if not manifests:
            fail("release published but manifest fetch returned nothing")
        manifest = manifests[0]
        if args.full_verify:
            # The RSM is msgpack; artifact names appear as plain strings in it.
            names = {
                raw.decode()
                for raw in re.findall(
                    rb"[\w.\-]+\.(?:whl|pyz|tar\.gz|zip)", manifest.read_bytes()
                )
            }
            names -= {f"manifest.{_MSG_EXT}"}
            for name in sorted(names):
                fetch_args = argparse.Namespace(
                    **{**vars(args), "target": f"{args.tag}:{name}", "dest": tmp}
                )
                rc = cmd_fetch(fetch_args)
                if rc != 0:
                    return rc
        return cmd_verify_manifest(args, manifest)


def cmd_verify_manifest(args, manifest: Path) -> int:
    return run_rngit(args, ["-o", str(manifest), "verify"], cwd=manifest.parent)


def cmd_raw(args) -> int:
    argv = [rngit_python(), "-m", RNGIT_MODULE, *args.rngit_args]
    argv += ["-v"] * args.verbose + ["-q"] * args.quiet
    return subprocess.run(argv, cwd=ROOT).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rngit_release.py",
        description="MeshChatX rngit release helper (build, create, fetch, verify, delete).",
    )
    parser.add_argument(
        "--remote", help="rngit remote URL (env MESHCHATX_RNGIT_REMOTE)"
    )
    parser.add_argument(
        "--identity",
        help="release identity file (env RNGIT_IDENTITY, default rngit client_identity)",
    )
    parser.add_argument(
        "--signer", help="signing identity file if different (env RNGIT_SIGNER)"
    )
    parser.add_argument("--config", help="alternative rngit config directory")
    parser.add_argument("--rnsconfig", help="alternative Reticulum config directory")
    parser.add_argument(
        "--artifacts-dir",
        help="release artifacts dir (env MESHCHATX_RNGIT_ARTIFACTS, default python-dist)",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="rngit verbosity"
    )
    parser.add_argument(
        "-q", "--quiet", action="count", default=0, help="rngit quietness"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="build wheel and pyz into the artifacts dir")
    p.add_argument("--skip-wheel", action="store_true")
    p.add_argument("--skip-pyz", action="store_true")
    p.set_defaults(func=cmd_build)

    sub.add_parser("list", help="list releases on the remote").set_defaults(
        func=lambda a: cmd_simple(a, "list")
    )
    sub.add_parser("latest", help="show the latest release tag").set_defaults(
        func=lambda a: cmd_simple(a, "latest")
    )

    p = sub.add_parser("view", help="show one release")
    p.add_argument("tag")
    p.set_defaults(func=lambda a: cmd_simple(a, "view", a.tag))

    p = sub.add_parser(
        "fetch",
        help="fetch release artifacts, e.g. 'v4.9.0:manifest.rsm' or 'latest:name'",
    )
    p.add_argument("target")
    p.add_argument("--dest", help="download directory (default: cwd)")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser(
        "verify", help="offline-verify a fetched manifest and its artifacts"
    )
    p.add_argument("manifest", help="path to the .rsm manifest file")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("create", help="create a release from the artifacts dir")
    p.add_argument("tag")
    p.add_argument(
        "-n", "--name", help="package name in the manifest (default: repo name)"
    )
    notes = p.add_mutually_exclusive_group()
    notes.add_argument("--notes", help="release notes text")
    notes.add_argument("--notes-file", help="path to a markdown notes file")
    notes.add_argument(
        "--changelog",
        action="store_true",
        help="use the CHANGELOG section for this tag",
    )
    notes.add_argument("--edit", action="store_true", help="open $EDITOR interactively")
    p.add_argument(
        "-L",
        "--local",
        action="store_true",
        help="generate manifest and signatures without uploading",
    )
    p.set_defaults(func=cmd_create)

    p = sub.add_parser(
        "delete", help="delete a release (immutable once published; use with care)"
    )
    p.add_argument("tag")
    p.add_argument(
        "--yes", action="store_true", help="answer yes to the confirmation prompt"
    )
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("release", help="build + create + verify in one shot")
    p.add_argument("tag")
    p.add_argument("-n", "--name", help="package name in the manifest")
    notes = p.add_mutually_exclusive_group()
    notes.add_argument("--notes", help="release notes text")
    notes.add_argument("--notes-file", help="path to a markdown notes file")
    notes.add_argument(
        "--changelog",
        action="store_true",
        help="use the CHANGELOG section for this tag",
    )
    notes.add_argument("--edit", action="store_true", help="open $EDITOR interactively")
    p.add_argument("--skip-wheel", action="store_true")
    p.add_argument("--skip-pyz", action="store_true")
    p.add_argument(
        "--no-verify", action="store_true", help="skip the post-publish verify"
    )
    p.add_argument(
        "--full-verify",
        action="store_true",
        help="fetch every artifact, not just the manifest",
    )
    p.set_defaults(func=cmd_release)

    p = sub.add_parser(
        "raw",
        help="pass arguments straight to rngit (work, perms, sync, mirror, node...)",
    )
    p.add_argument("rngit_args", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_raw)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
