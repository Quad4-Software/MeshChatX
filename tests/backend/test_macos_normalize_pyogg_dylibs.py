# SPDX-License-Identifier: 0BSD

"""Tests for scripts/ci/macos-normalize-pyogg-dylibs.sh.

LXST vendors x86_64-only pyogg dylibs under
LXST/Codecs/libs/pyogg/libs/macos/. The script must swap them for
native-arch builds (Homebrew on arm64, MacPorts on x86_64), pull in the
package-manager dependency closure, and repoint ids/refs at @loader_path.
Everything runs through PATH stubs so the tests work on Linux CI.

Fake dylib files are plain text standing in for Mach-O:
  line 1:  arch token ("arm64" or "x86_64")
  line 2:  install name (id)
  line 3+: load-command refs (deps)
The file/otool/install_name_tool stubs operate on that format.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

_SCRIPT = Path("scripts/ci/macos-normalize-pyogg-dylibs.sh")


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _dylib(arch: str, install_name: str, *refs: str) -> bytes:
    lines = "\n".join([arch, install_name, *refs])
    return f"{lines}\n".encode()


def _pyogg_dir(tmp_path: Path) -> Path:
    libs = tmp_path / "lxst" / "LXST" / "Codecs" / "libs" / "pyogg" / "libs" / "macos"
    libs.mkdir(parents=True)
    return libs


def _fake_darwin(
    tmp_path: Path,
    *,
    target_arch: str,
    pyogg_dir: Path,
    brew_prefix: Path | None = None,
) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    tool_log = tmp_path / "install-name-tool.log"

    _write_exec(
        bin_dir / "uname",
        '#!/bin/sh\nif [ "$1" = "-s" ]; then echo Darwin; exit 0; fi\necho Darwin\n',
    )
    _write_exec(
        bin_dir / "file",
        "#!/bin/sh\n"
        'f=""\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in --brief|--no-pad) shift ;; *) f="$1"; shift ;; esac\n'
        "done\n"
        'arch=$(head -n1 "$f" 2>/dev/null)\n'
        'case "$arch" in\n'
        "  arm64|x86_64)\n"
        '    echo "Mach-O 64-bit dynamically linked shared library $arch"\n'
        "    ;;\n"
        '  *) echo "ASCII text" ;;\n'
        "esac\n",
    )
    _write_exec(
        bin_dir / "otool",
        "#!/bin/sh\n"
        'f=""\n'
        'while [ "$#" -gt 0 ]; do f="$1"; shift; done\n'
        'echo "$f:"\n'
        'tail -n +2 "$f" 2>/dev/null | while IFS= read -r ref; do\n'
        '  [ -n "$ref" ] && echo "  $ref (compatibility version 0.0.0, current version 0.0.0)"\n'
        "done\n",
    )
    _write_exec(
        bin_dir / "install_name_tool",
        "#!/bin/sh\n"
        f'echo "$@" >>"{tool_log}"\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in\n'
        "    -change)\n"
        '      sed -i "s|^${2}$|${3}|" "$4"\n'
        "      shift 4 ;;\n"
        "    -id)\n"
        '      f="$3"\n'
        '      awk -v new="$2" \'NR==2 {print new; next} {print}\' "$f" >"$f.tmp"\n'
        '      mv "$f.tmp" "$f"\n'
        "      shift 3 ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "exit 0\n",
    )
    _write_exec(bin_dir / "codesign", "#!/bin/sh\nexit 0\n")
    if brew_prefix is not None:
        _write_exec(
            bin_dir / "brew",
            "#!/bin/sh\n"
            'if [ "$1" = "--prefix" ]; then\n'
            f'  p="{brew_prefix}/$2"\n'
            '  if [ -d "$p" ]; then echo "$p"; exit 0; fi\n'
            "  exit 1\n"
            "fi\n"
            "exit 1\n",
        )
    _write_exec(
        tmp_path / "fake-python",
        "#!/bin/sh\n"
        'case "$2" in\n'
        f'  *platform.machine*) echo "{target_arch}" ;;\n'
        f'  *) echo "{pyogg_dir}" ;;\n'
        "esac\n",
    )
    return bin_dir


def _run(tmp_path: Path, *extra_env: tuple[str, str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    env.update(dict(extra_env))
    return subprocess.run(  # nosec: BAN-B607
        ["bash", str(_SCRIPT), str(tmp_path / "fake-python")],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _brew_lib(prefix: Path, formula: str, name: str, body: bytes) -> Path:
    lib = prefix / formula / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    path = lib / name
    path.write_bytes(body)
    return path


def test_replaces_wrong_arch_dylib_from_brew(tmp_path: Path) -> None:
    pyogg_dir = _pyogg_dir(tmp_path)
    vendored = _dylib("x86_64", "@loader_path/libopus.0.dylib")
    (pyogg_dir / "libopus.0.dylib").write_bytes(vendored)
    brew = tmp_path / "brew"
    brew_lib = _brew_lib(
        brew,
        "opus",
        "libopus.0.dylib",
        _dylib("arm64", f"{brew}/opus/lib/libopus.0.dylib"),
    )
    _fake_darwin(tmp_path, target_arch="arm64", pyogg_dir=pyogg_dir, brew_prefix=brew)

    result = _run(tmp_path, ("MESHCHATX_PYOGG_LIB_ROOTS", str(brew)))

    assert result.returncode == 0, result.stderr + result.stdout
    content = (pyogg_dir / "libopus.0.dylib").read_text(encoding="utf-8")
    assert content.splitlines()[0] == "arm64"
    # -id rewrote the install name to @loader_path/<basename>
    assert "@loader_path/libopus.0.dylib" in content.splitlines()[1]
    logged = (tmp_path / "install-name-tool.log").read_text(encoding="utf-8")
    assert "-id @loader_path/libopus.0.dylib" in logged
    assert f"replaced libopus.0.dylib with {brew_lib}" in result.stdout


def test_keeps_matching_arch_dylibs(tmp_path: Path) -> None:
    pyogg_dir = _pyogg_dir(tmp_path)
    vendored = _dylib("x86_64", "@loader_path/libopus.0.dylib")
    (pyogg_dir / "libopus.0.dylib").write_bytes(vendored)
    _fake_darwin(tmp_path, target_arch="x86_64", pyogg_dir=pyogg_dir)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert (pyogg_dir / "libopus.0.dylib").read_bytes() == vendored
    assert "nothing to do" in result.stdout


def test_fails_when_no_native_build_available(tmp_path: Path) -> None:
    pyogg_dir = _pyogg_dir(tmp_path)
    (pyogg_dir / "libopus.0.dylib").write_bytes(
        _dylib("x86_64", "@loader_path/libopus.0.dylib"),
    )
    _fake_darwin(tmp_path, target_arch="arm64", pyogg_dir=pyogg_dir)

    result = _run(tmp_path, ("MESHCHATX_PYOGG_LIB_ROOTS", str(tmp_path / "empty")))

    assert result.returncode != 0
    assert "no arm64 build found" in result.stderr


def test_bundles_dependency_closure(tmp_path: Path) -> None:
    pyogg_dir = _pyogg_dir(tmp_path)
    (pyogg_dir / "libopusfile.0.dylib").write_bytes(
        _dylib("x86_64", "@loader_path/libopusfile.0.dylib"),
    )
    brew = tmp_path / "brew"
    openssl_lib = brew / "openssl@3" / "lib"
    openssl_lib.mkdir(parents=True)
    crypto = openssl_lib / "libcrypto.3.dylib"
    crypto.write_bytes(
        _dylib("arm64", f"{openssl_lib}/libcrypto.3.dylib"),
    )
    _brew_lib(
        brew,
        "opusfile",
        "libopusfile.0.dylib",
        _dylib(
            "arm64",
            f"{brew}/opusfile/lib/libopusfile.0.dylib",
            f"{openssl_lib}/libcrypto.3.dylib",
        ),
    )
    _fake_darwin(tmp_path, target_arch="arm64", pyogg_dir=pyogg_dir, brew_prefix=brew)

    result = _run(tmp_path, ("MESHCHATX_PYOGG_LIB_ROOTS", str(brew)))

    assert result.returncode == 0, result.stderr + result.stdout
    # The openssl dep was copied in next to the vendored set.
    bundled = pyogg_dir / "libcrypto.3.dylib"
    assert bundled.read_text(encoding="utf-8").splitlines()[0] == "arm64"
    # opusfile's dep ref was repointed at @loader_path.
    opusfile = (pyogg_dir / "libopusfile.0.dylib").read_text(encoding="utf-8")
    assert "@loader_path/libcrypto.3.dylib" in opusfile.splitlines()
    assert f"{openssl_lib}/libcrypto.3.dylib" not in opusfile.splitlines()
    logged = (tmp_path / "install-name-tool.log").read_text(encoding="utf-8")
    assert (
        f"-change {openssl_lib}/libcrypto.3.dylib @loader_path/libcrypto.3.dylib"
        in logged
    )


def test_fails_on_unresolvable_managed_ref(tmp_path: Path) -> None:
    pyogg_dir = _pyogg_dir(tmp_path)
    (pyogg_dir / "libopusfile.0.dylib").write_bytes(
        _dylib("x86_64", "@loader_path/libopusfile.0.dylib"),
    )
    brew = tmp_path / "brew"
    missing_dep = f"{brew}/missing/lib/libmissing.1.dylib"
    _brew_lib(
        brew,
        "opusfile",
        "libopusfile.0.dylib",
        _dylib(
            "arm64",
            f"{brew}/opusfile/lib/libopusfile.0.dylib",
            missing_dep,
        ),
    )
    _fake_darwin(tmp_path, target_arch="arm64", pyogg_dir=pyogg_dir, brew_prefix=brew)

    result = _run(tmp_path, ("MESHCHATX_PYOGG_LIB_ROOTS", str(brew)))

    # The dep does not exist on disk, so it cannot be bundled or rewritten.
    assert result.returncode != 0
    assert "unresolved ref" in result.stderr
    assert missing_dep in result.stderr


def test_skips_non_darwin(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(bin_dir / "uname", "#!/bin/sh\necho Linux\n")
    pyogg_dir = _pyogg_dir(tmp_path)
    _write_exec(
        tmp_path / "fake-python",
        "#!/bin/sh\n" + f'echo "{pyogg_dir}"\n',
    )
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "not macOS" in result.stderr


def test_missing_pyogg_dir_is_a_noop(tmp_path: Path) -> None:
    missing = tmp_path / "nowhere"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(
        bin_dir / "uname",
        '#!/bin/sh\nif [ "$1" = "-s" ]; then echo Darwin; exit 0; fi\necho Darwin\n',
    )
    _write_exec(
        tmp_path / "fake-python",
        "#!/bin/sh\n"
        'case "$2" in\n'
        '  *platform.machine*) echo "arm64" ;;\n'
        f'  *) echo "{missing}" ;;\n'
        "esac\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "not found" in result.stderr
