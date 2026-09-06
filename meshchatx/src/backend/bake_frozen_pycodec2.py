# SPDX-License-Identifier: 0BSD

"""Bundle libcodec2 next to frozen pycodec2 so dyld/dlopen can find it.

cx_Freeze rewrites Darwin load commands to @executable_path/lib/<id-basename>.
The published pycodec2 wheel ships libcodec2 under pycodec2/.dylibs/ with a
versioned id (libcodec2.1.2.dylib). The x64 sdist slice is copied as
libcodec2.dylib. If those layouts differ, unify-backend-plain-files.sh used
to delete both copies as arch-only Mach-O files, so the shipped .so still
named a dylib that was not in the app bundle. Import LXST then raised
ImportError at process start.
"""

from __future__ import annotations

import importlib.metadata
import shutil
import stat
import subprocess
import sys
from pathlib import Path

_CANONICAL_DYLIB = "libcodec2.dylib"
_CANONICAL_SO = "libcodec2.so"
_CANONICAL_DLL = "libcodec2.dll"
_LOADER_PATH_DYLIB = "@loader_path/libcodec2.dylib"


def _as_path(value: object) -> Path:
    return Path(str(value))


def _pycodec2_dist_dir() -> Path | None:
    """Return the installed pycodec2 package dir without importing the extension."""
    try:
        dist = importlib.metadata.distribution("pycodec2")
    except importlib.metadata.PackageNotFoundError:
        return None
    for rel in dist.files or ():
        parts = rel.parts
        if not parts or parts[0] != "pycodec2":
            continue
        located = _as_path(dist.locate_file(rel))
        if located.parent.name == "pycodec2":
            return located.parent.resolve()
        if located.name == "pycodec2" and located.is_dir():
            return located.resolve()
    locate = _as_path(dist.locate_file("pycodec2"))
    if locate.is_dir():
        return locate.resolve()
    return None


def _is_codec2_lib(name: str) -> bool:
    lower = name.lower()
    if lower.startswith("libcodec2") or lower.startswith("codec2"):
        return lower.endswith((".dylib", ".so", ".dll")) or ".so." in lower
    return False


def _iter_codec2_libs(root: Path, *, recursive: bool = True) -> list[Path]:
    found: list[Path] = []
    if not root.is_dir():
        return found
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        if not path.is_file():
            continue
        if _is_codec2_lib(path.name):
            found.append(path)
    return found


def _extension_module(pkg: Path) -> Path | None:
    matches = sorted(
        [
            path
            for path in pkg.iterdir()
            if path.is_file()
            and path.name.startswith("pycodec2")
            and path.suffix in {".so", ".pyd", ".dylib"}
        ],
    )
    return matches[0] if matches else None


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        dest.unlink()
    elif dest.exists():
        if src.resolve() == dest.resolve():
            return
        dest.chmod(stat.S_IWRITE | stat.S_IREAD)
        dest.unlink()
    shutil.copy2(src, dest)


def _darwin_load_commands(ext_so: Path) -> list[str]:
    otool = shutil.which("otool")
    if not otool:
        return []
    try:
        result = subprocess.run(
            [otool, "-L", str(ext_so)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    refs: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        ref = line.strip().split(" ", 1)[0]
        if "libcodec2" in ref or "/codec2" in ref:
            refs.append(ref)
    return refs


def _rewrite_darwin_extension(ext_so: Path, dylib: Path) -> None:
    refs = _darwin_load_commands(ext_so)
    install_name_tool = shutil.which("install_name_tool")
    if install_name_tool:
        for old_ref in refs:
            if old_ref == _LOADER_PATH_DYLIB:
                continue
            subprocess.run(
                [
                    install_name_tool,
                    "-change",
                    old_ref,
                    _LOADER_PATH_DYLIB,
                    str(ext_so),
                ],
                check=False,
            )
        subprocess.run(
            [install_name_tool, "-id", _LOADER_PATH_DYLIB, str(dylib)],
            check=False,
        )
    codesign = shutil.which("codesign")
    if codesign:
        subprocess.run(
            [codesign, "--force", "--sign", "-", str(ext_so), str(dylib)],
            check=False,
            capture_output=True,
        )


def _prune_pkg_extra_codec2(pkg: Path, keep_name: str) -> None:
    for path in pkg.iterdir():
        if path.name == keep_name:
            continue
        if not (path.is_file() or path.is_symlink()):
            continue
        if _is_codec2_lib(path.name):
            path.unlink()


def _pick_source_lib(candidates: list[Path]) -> Path | None:
    if not candidates:
        return None
    for path in candidates:
        if path.name in {_CANONICAL_DYLIB, _CANONICAL_SO, _CANONICAL_DLL}:
            return path
    return candidates[0]


def bake_frozen_pycodec2(build_dir: Path) -> None:
    """Copy libcodec2 into freeze-stable paths next to pycodec2 and under lib/."""
    lib_dir = build_dir / "lib"
    pkg = lib_dir / "pycodec2"
    if not pkg.is_dir():
        raise SystemExit(f"bake_frozen_pycodec2: missing {pkg}")

    ext_so = _extension_module(pkg)
    if ext_so is None:
        raise SystemExit(f"bake_frozen_pycodec2: no pycodec2 extension under {pkg}")

    candidates = _iter_codec2_libs(pkg) + _iter_codec2_libs(lib_dir, recursive=False)
    dist_dir = _pycodec2_dist_dir()
    if dist_dir is not None:
        candidates.extend(_iter_codec2_libs(dist_dir))

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)

    source = _pick_source_lib(unique)
    if source is None:
        if sys.platform == "darwin":
            raise SystemExit(
                "bake_frozen_pycodec2: libcodec2 not found next to frozen pycodec2 "
                "or in the build environment. The macOS app will crash on import LXST.",
            )
        print("bake_frozen_pycodec2: libcodec2 not bundled, skipping")
        return

    if source.suffix == ".dll" or source.name.lower().endswith(".dll"):
        canonical_name = _CANONICAL_DLL
    elif source.suffix == ".dylib" or ".dylib" in source.name:
        canonical_name = _CANONICAL_DYLIB
    else:
        canonical_name = _CANONICAL_SO

    dest_pkg = pkg / canonical_name
    dest_lib = lib_dir / canonical_name
    destinations = {dest_pkg, dest_lib}
    if canonical_name == _CANONICAL_DYLIB:
        destinations.add(lib_dir / "libcodec2.1.2.dylib")
    if source.name != canonical_name:
        destinations.add(lib_dir / source.name)
    for ref in _darwin_load_commands(ext_so):
        base = Path(ref).name
        if _is_codec2_lib(base):
            destinations.add(lib_dir / base)
    for dest in destinations:
        _copy_file(source, dest)

    dylibs_dir = pkg / ".dylibs"
    if dylibs_dir.is_dir():
        shutil.rmtree(dylibs_dir)
    _prune_pkg_extra_codec2(pkg, canonical_name)

    if sys.platform == "darwin" and dest_pkg.suffix == ".dylib":
        _rewrite_darwin_extension(ext_so, dest_pkg)

    print(
        "bake_frozen_pycodec2: OK "
        f"ext={ext_so.name} lib={canonical_name} src={source.name}",
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: python -m meshchatx.src.backend.bake_frozen_pycodec2 <build dir>",
        )
    bake_frozen_pycodec2(Path(sys.argv[1]).resolve())


if __name__ == "__main__":
    main()
