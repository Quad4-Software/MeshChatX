#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Sync dependency pins from versions.toml into the build files.

Reads versions.toml (single source) and rewrites matching specifiers in:

  - pyproject.toml [project].dependencies          ([shared] + [pyproject])
  - android/app/build.gradle install "name..."     ([shared] + [android.pip])
  - android/app/build.gradle vendor wheel paths    ([android.wheels])

Only the version token right after the first operator is replaced, so
operators, upper bounds, extras and markers are preserved. After the file
rewrites, uv lock and uv export --no-dev -o requirements.txt refresh the
lock outputs unless --no-lock is given.

Usage:

    python3 scripts/sync_deps.py                 # sync everything
    python3 scripts/sync_deps.py lxmf=1.2.0      # set + sync, all sections
    python3 scripts/sync_deps.py android.pip.bcrypt=3.1.8
    python3 scripts/sync_deps.py --no-lock       # file rewrites only

Then refresh generated artifacts:

    task licenses:refresh
    pnpm run build-repository-wheels
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = ROOT / "versions.toml"
PYPROJECT = ROOT / "pyproject.toml"
GRADLE = ROOT / "android" / "app" / "build.gradle"

SECTION_PYPROJECT = "pyproject"
SECTION_ANDROID_PIP = "android.pip"
SECTION_ANDROID_WHEELS = "android.wheels"
SECTION_SHARED = "shared"


def _name_re(name: str) -> str:
    return re.escape(name).replace(r"\-", "[-_]")


_SPEC_OPS = r"(?:===|==|>=|<=|~=|!=|>|<)"


def _spec_pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        r"(?i)\b(" + _name_re(name) + r")"
        r"(\s*(?:\[[^\]]*\])?\s*\(?\s*" + _SPEC_OPS + r"\s*)"
        r"([0-9][A-Za-z0-9.*!+]*)"
        r"(?=[,;\)\s'\"]|$)"
    )


def _wheel_pattern(name: str) -> re.Pattern[str]:
    wf = re.escape(name.replace("-", "_"))
    return re.compile(
        r"(?i)(vendor[/\\]" + wf + r"-)[0-9][A-Za-z0-9.]*(-py3-none-any\.whl)"
    )


def _patch_spec_lines(
    text: str, name: str, version: str, line_match
) -> tuple[str, int]:
    pat = _spec_pattern(name)
    hits = 0
    out = []
    for line in text.splitlines(keepends=True):
        if line_match(line) and pat.search(line):
            line = pat.sub(lambda m: m.group(1) + m.group(2) + version, line, count=1)
            hits += 1
        out.append(line)
    return "".join(out), hits


def _patch_pyproject(name: str, version: str) -> int:
    text = PYPROJECT.read_text(encoding="utf-8")
    in_deps = False
    out = []
    hits = 0
    pat = _spec_pattern(name)
    for line in text.splitlines(keepends=True):
        if re.match(r"\s*dependencies\s*=\s*\[", line):
            in_deps = True
        elif in_deps and line.strip() == "]":
            in_deps = False
        elif in_deps and pat.search(line):
            line = pat.sub(lambda m: m.group(1) + m.group(2) + version, line, count=1)
            hits += 1
        out.append(line)
    next_text = "".join(out)
    if next_text != text:
        PYPROJECT.write_text(next_text, encoding="utf-8")
    return hits


def _patch_gradle_installs(text: str, name: str, version: str) -> tuple[str, int]:
    return _patch_spec_lines(
        text, name, version, lambda line: re.match(r"\s*install\s*\"", line)
    )


def _patch_gradle_wheels(text: str, name: str, version: str) -> tuple[str, int]:
    pat = _wheel_pattern(name)
    hits = len(pat.findall(text))
    return pat.sub(lambda m: m.group(1) + version + m.group(2), text), hits


def _load() -> dict[str, dict[str, str]]:
    """Flatten versions.toml to {dotted_section: {name: version}}."""
    with VERSIONS.open("rb") as fh:
        raw = tomllib.load(fh)
    flat: dict[str, dict[str, str]] = {}
    for sec, table in raw.items():
        for k, v in table.items():
            if isinstance(v, dict):
                flat[f"{sec}.{k}"] = v
            else:
                flat.setdefault(sec, {})[k] = v
    return flat


def _set_version(dotted: str, version: str) -> list[str]:
    parts = dotted.split(".")
    key = parts[-1]
    wanted = [".".join(parts[:-1])] if len(parts) > 1 else None

    flat = _load()
    targets = [
        sec
        for sec, table in flat.items()
        if key in table and (wanted is None or sec in wanted)
    ]
    if not targets:
        raise SystemExit(f"sync_deps: no '{key}' entry found in versions.toml")

    lines = VERSIONS.read_text(encoding="utf-8").splitlines(keepends=True)
    section = ""
    key_re = re.compile(rf"^({re.escape(key)}\s*=\s*)\"[^\"]*\"")
    header_re = re.compile(r"^\[([^\]]+)\]")
    for i, line in enumerate(lines):
        m = header_re.match(line)
        if m:
            section = m.group(1)
            continue
        if section in targets and (mm := key_re.match(line)):
            lines[i] = mm.group(1) + f'"{version}"' + line[mm.end() :]
    VERSIONS.write_text("".join(lines), encoding="utf-8")
    return targets


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(f"sync_deps: {' '.join(cmd)} failed ({proc.returncode})")


def main(argv: list[str]) -> int:
    no_lock = "--no-lock" in argv
    sets = [a for a in argv if "=" in a and not a.startswith("-")]
    for spec in sets:
        dotted, _, version = spec.partition("=")
        touched = _set_version(dotted.strip(), version.strip())
        for full in touched:
            print(f"versions.toml [{full}]: set to {version}")

    data = _load()
    shared = data.get(SECTION_SHARED, {})
    pyproject_deps = data.get(SECTION_PYPROJECT, {})
    android_pip = data.get(SECTION_ANDROID_PIP, {})
    android_wheels = data.get(SECTION_ANDROID_WHEELS, {})

    gradle_text = GRADLE.read_text(encoding="utf-8")
    gradle_orig = gradle_text
    hits = {}

    for name, version in {**shared, **pyproject_deps}.items():
        n = _patch_pyproject(name, version)
        if n:
            print(f"pyproject.toml: {name} -> {version}")
        hits[(SECTION_PYPROJECT, name)] = n

    for name, version in {**shared, **android_pip}.items():
        gradle_text, n = _patch_gradle_installs(gradle_text, name, version)
        if n:
            print(f"build.gradle: {name} -> {version}")
        hits[(SECTION_ANDROID_PIP, name)] = n

    for name, version in android_wheels.items():
        gradle_text, n = _patch_gradle_wheels(gradle_text, name, version)
        hits[(SECTION_ANDROID_WHEELS, name)] = n
        if n:
            print(f"build.gradle wheel: {name} -> {version}")
            whl = (
                GRADLE.parent.parent
                / "vendor"
                / f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
            )
            if not whl.exists():
                print(f"warning: {whl.name} missing in android/vendor", file=sys.stderr)

    if gradle_text != gradle_orig:
        GRADLE.write_text(gradle_text, encoding="utf-8")

    misses = []
    for sec, table in (
        (SECTION_SHARED, shared),
        (SECTION_PYPROJECT, pyproject_deps),
        (SECTION_ANDROID_PIP, android_pip),
        (SECTION_ANDROID_WHEELS, android_wheels),
    ):
        for name in table:
            total = hits.get((SECTION_PYPROJECT, name), 0) + hits.get(
                (SECTION_ANDROID_PIP, name), 0
            )
            if sec == SECTION_ANDROID_WHEELS:
                total = hits.get((SECTION_ANDROID_WHEELS, name), 0)
            if total == 0:
                misses.append(f"{sec}:{name}")
    if misses:
        print("warning: no match for: " + ", ".join(misses), file=sys.stderr)

    if not no_lock:
        _run(["uv", "lock"])
        _run(["uv", "export", "--no-dev", "-o", "requirements.txt"])
        print("uv.lock + requirements.txt refreshed")
    else:
        print("--no-lock: skipped uv lock and requirements.txt export")

    print("follow-ups: task licenses:refresh, pnpm run build-repository-wheels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
