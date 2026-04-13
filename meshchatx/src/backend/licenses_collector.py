"""Collect third-party license metadata for Python (backend) and Node (frontend)."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

_ROOT_DIST_CANDIDATES = ("reticulum-meshchatx", "reticulum_meshchatx")


def _repo_root() -> Path:
    import meshchatx

    return Path(meshchatx.__file__).resolve().parent.parent


def _license_from_metadata(meta: importlib.metadata.Metadata) -> str:
    le = meta.get("License-Expression")
    if le:
        return str(le).strip()
    lic = meta.get("License")
    if lic and str(lic).strip() and str(lic).strip().upper() != "UNKNOWN":
        return str(lic).strip()
    classifiers = meta.get_all("Classifier") or []
    for line in classifiers:
        if line.startswith("License ::"):
            return line.split("::", 1)[-1].strip()
    return "—"


def _author_from_metadata(meta: importlib.metadata.Metadata) -> str:
    a = (meta.get("Author") or "").strip()
    if a:
        return a
    ae = (meta.get("Author-email") or "").strip()
    if ae:
        return ae
    m = (meta.get("Maintainer") or "").strip()
    if m:
        return m
    return "—"


def _dist_for_requirement_name(name: str) -> importlib.metadata.Distribution | None:
    key = canonicalize_name(name)
    try:
        return importlib.metadata.distribution(key)
    except importlib.metadata.PackageNotFoundError:
        pass
    try:
        return importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _collect_python_transitive(root_names: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(name: str) -> None:
        cname = canonicalize_name(name)
        if cname in seen:
            return
        dist = _dist_for_requirement_name(name)
        if dist is None:
            return
        seen.add(cname)
        meta = dist.metadata
        pkg_name = meta.get("Name") or name
        rows.append(
            {
                "name": str(pkg_name),
                "version": dist.version,
                "author": _author_from_metadata(meta),
                "license": _license_from_metadata(meta),
            },
        )
        for req_str in dist.requires or []:
            if not (req_str or "").strip():
                continue
            try:
                req = Requirement(req_str)
            except Exception:
                continue
            if req.extras and not req.marker:
                pass
            if req.marker is not None and not req.marker.evaluate():
                continue
            visit(req.name)

    for root in root_names:
        visit(root)

    rows.sort(key=lambda r: r["name"].lower())
    return rows


def _python_roots_from_pyproject(repo_root: Path) -> tuple[str, ...]:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        return _ROOT_DIST_CANDIDATES[:1]
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except OSError:
        return _ROOT_DIST_CANDIDATES[:1]
    deps = (data.get("project") or {}).get("dependencies") or []
    names: list[str] = []
    for line in deps:
        try:
            req = Requirement(line)
        except Exception:
            continue
        names.append(req.name)
    if not names:
        return _ROOT_DIST_CANDIDATES[:1]
    return tuple(sorted(set(names), key=lambda n: n.lower()))


def collect_backend_licenses() -> list[dict[str, Any]]:
    for root in _ROOT_DIST_CANDIDATES:
        if _dist_for_requirement_name(root) is not None:
            return _collect_python_transitive((root,))
    repo = _repo_root()
    roots = _python_roots_from_pyproject(repo)
    return _collect_python_transitive(roots)


def _flatten_pnpm_licenses_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for _license_key, packages in data.items():
        if not isinstance(packages, list):
            continue
        for pkg in packages:
            if not isinstance(pkg, dict):
                continue
            name = pkg.get("name") or "?"
            versions = pkg.get("versions") or []
            version = versions[0] if versions else "?"
            author = pkg.get("author") or "—"
            if not isinstance(author, str):
                author = str(author)
            lic = pkg.get("license") or _license_key or "—"
            out.append(
                {
                    "name": name,
                    "version": str(version),
                    "author": author,
                    "license": str(lic),
                },
            )
    out.sort(key=lambda r: r["name"].lower())
    return out


def _load_embedded_frontend_licenses() -> list[dict[str, Any]] | None:
    data_dir = Path(__file__).resolve().parent / "data"
    path = data_dir / "licenses_frontend.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, list):
        return None
    return [x for x in raw if isinstance(x, dict)]


def collect_frontend_licenses() -> tuple[list[dict[str, Any]], str]:
    embedded = _load_embedded_frontend_licenses()
    repo = _repo_root()
    if not (repo / "package.json").is_file():
        if embedded is not None:
            return embedded, "embedded"
        return [], "none"

    pnpm = shutil.which("pnpm")
    if pnpm:
        try:
            proc = subprocess.run(
                [pnpm, "licenses", "list", "--json"],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                parsed = json.loads(proc.stdout)
                if isinstance(parsed, dict):
                    return _flatten_pnpm_licenses_json(parsed), "pnpm"
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass

    if embedded is not None:
        return embedded, "embedded"

    return [], "none"


def build_licenses_payload() -> dict[str, Any]:
    backend = collect_backend_licenses()
    frontend, fe_source = collect_frontend_licenses()
    return {
        "backend": backend,
        "frontend": frontend,
        "meta": {
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "backend_count": len(backend),
            "frontend_count": len(frontend),
            "frontend_source": fe_source,
        },
    }
