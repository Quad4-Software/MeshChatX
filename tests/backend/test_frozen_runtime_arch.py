# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

_THIN = Path("scripts/thin-backend-mach-o.sh")
_VERIFY = Path("scripts/ci/github-verify-frozen-runtime.sh")
_UNIFY = Path("scripts/unify-backend-plain-files.sh")


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _fake_darwin_bin(tmp_path: Path, *, uname_m: str = "arm64") -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exec(
        bin_dir / "uname",
        "#!/bin/sh\n"
        'if [ "$1" = "-s" ]; then echo Darwin; exit 0; fi\n'
        f'if [ "$1" = "-m" ]; then echo {uname_m}; exit 0; fi\n'
        "echo Darwin\n",
    )
    return bin_dir


def _frozen_tree(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _write_exec(
        root / "ReticulumMeshChatX",
        "#!/bin/sh\necho frozen-freeze-probe ok\nexit 0\n",
    )
    email = root / "lib" / "email"
    email.mkdir(parents=True)
    (email / "header.py").write_text("# header\n", encoding="utf-8")
    return root


def test_thin_backend_find_includes_all_mach_o() -> None:
    text = _THIN.read_text(encoding="utf-8")
    assert 'find "$tree" -type f -print0' in text
    assert '-name "*.so"' not in text
    assert "MESHCHATX_THIN_ARM64_DIR" in text
    assert "ReticulumMeshChatX stub" in text


def test_thin_backend_thins_executable_not_only_dylibs(tmp_path: Path) -> None:
    arm = tmp_path / "arm"
    x64 = tmp_path / "x64"
    for tree in (arm, x64):
        (tree / "lib").mkdir(parents=True)
        (tree / "ReticulumMeshChatX").write_bytes(b"fat-exe")
        (tree / "ReticulumMeshChatX").chmod(0o755)
        (tree / "lib" / "zlib.cpython-314-darwin.so").write_bytes(b"fat-so")
        (tree / "readme.txt").write_text("leave me", encoding="utf-8")

    bin_dir = _fake_darwin_bin(tmp_path)
    _write_exec(
        bin_dir / "file",
        "#!/bin/sh\n"
        'f="$1"\n'
        'while [ "$#" -gt 0 ]; do f="$1"; shift; done\n'
        'base=$(basename "$f")\n'
        'case "$base" in\n'
        "ReticulumMeshChatX|zlib.cpython-314-darwin.so)\n"
        '  echo "Mach-O universal binary with 2 architectures: x86_64 arm64"\n'
        "  ;;\n"
        '*) echo "ASCII text" ;;\n'
        "esac\n",
    )
    _write_exec(
        bin_dir / "lipo",
        "#!/bin/sh\n"
        'if [ "$1" = "-archs" ]; then echo "x86_64 arm64"; exit 0; fi\n'
        'if [ "$1" = "-thin" ]; then\n'
        '  arch="$2"\n'
        '  out=""\n'
        '  while [ "$#" -gt 0 ]; do\n'
        '    if [ "$1" = "-output" ]; then out="$2"; shift 2; continue; fi\n'
        "    shift\n"
        "  done\n"
        '  printf "thinned-%s\\n" "$arch" >"$out"\n'
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["MESHCHATX_THIN_ARM64_DIR"] = str(arm)
    env["MESHCHATX_THIN_X64_DIR"] = str(x64)
    result = subprocess.run(
        ["bash", str(_THIN)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert (arm / "ReticulumMeshChatX").read_text(encoding="utf-8") == "thinned-arm64\n"
    assert (x64 / "ReticulumMeshChatX").read_text(
        encoding="utf-8"
    ) == "thinned-x86_64\n"
    assert (arm / "lib" / "zlib.cpython-314-darwin.so").read_text(
        encoding="utf-8"
    ) == "thinned-arm64\n"
    assert (x64 / "lib" / "zlib.cpython-314-darwin.so").read_text(
        encoding="utf-8"
    ) == "thinned-x86_64\n"
    assert (arm / "readme.txt").read_text(encoding="utf-8") == "leave me"


def test_verify_frozen_runtime_uses_arch_x86_64_for_darwin_x64(
    tmp_path: Path,
) -> None:
    root = _frozen_tree(tmp_path / "darwin-x64")
    marker = tmp_path / "arch-used"
    bin_dir = _fake_darwin_bin(tmp_path, uname_m="arm64")
    _write_exec(
        bin_dir / "lipo",
        '#!/bin/sh\nif [ "$1" = "-archs" ]; then echo "x86_64"; exit 0; fi\nexit 1\n',
    )
    _write_exec(
        bin_dir / "arch",
        "#!/bin/sh\n"
        f'echo "$1" >"{marker}"\n'
        'if [ "$1" = "-x86_64" ]; then shift; exec "$@"; fi\n'
        "exit 1\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        ["bash", str(_VERIFY), str(root)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert marker.read_text(encoding="utf-8").strip() == "-x86_64"
    assert "using arch -x86_64" in result.stdout
    assert "frozen runtime verify: OK" in result.stdout


def test_verify_frozen_runtime_runs_native_on_darwin_arm64(tmp_path: Path) -> None:
    root = _frozen_tree(tmp_path / "darwin-arm64")
    marker = tmp_path / "arch-used"
    bin_dir = _fake_darwin_bin(tmp_path, uname_m="arm64")
    _write_exec(
        bin_dir / "lipo",
        '#!/bin/sh\nif [ "$1" = "-archs" ]; then echo "arm64"; exit 0; fi\nexit 1\n',
    )
    _write_exec(
        bin_dir / "arch",
        f'#!/bin/sh\necho "$1" >"{marker}"\nexit 1\n',
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        ["bash", str(_VERIFY), str(root)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert not marker.exists()
    assert "using arch" not in result.stdout
    assert "frozen runtime verify: OK" in result.stdout


def test_verify_frozen_runtime_rejects_arm64_only_stub_in_x64_tree(
    tmp_path: Path,
) -> None:
    root = _frozen_tree(tmp_path / "darwin-x64")
    bin_dir = _fake_darwin_bin(tmp_path, uname_m="arm64")
    _write_exec(
        bin_dir / "lipo",
        '#!/bin/sh\nif [ "$1" = "-archs" ]; then echo "arm64"; exit 0; fi\nexit 1\n',
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        ["bash", str(_VERIFY), str(root)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "cannot run as x86_64" in result.stderr


def _unify_file_stub(bin_dir: Path) -> None:
    _write_exec(
        bin_dir / "file",
        "#!/bin/sh\n"
        'f=""\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  case "$1" in\n'
        "    --brief|--no-pad) shift; continue ;;\n"
        '    *) f="$1"; shift ;;\n'
        "  esac\n"
        "done\n"
        'base=$(basename "$f")\n'
        'case "$base" in\n'
        "  *.dylib|*.so)\n"
        '    echo "Mach-O 64-bit dynamically linked shared library x86_64"\n'
        "    ;;\n"
        '  *) echo "ASCII text" ;;\n'
        "esac\n",
    )


def test_unify_mirrors_x64_openblas_and_still_drops_other_arch_only_mach_o(
    tmp_path: Path,
) -> None:
    arm = tmp_path / "arm"
    x64 = tmp_path / "x64"
    (arm / "lib" / "numpy" / ".dylibs").mkdir(parents=True)
    (x64 / "lib" / "numpy" / ".dylibs").mkdir(parents=True)
    (x64 / "lib" / "wasmtime" / "darwin-x86_64").mkdir(parents=True)
    (arm / "readme.txt").write_text("same", encoding="utf-8")
    (x64 / "readme.txt").write_text("same", encoding="utf-8")
    openblas = b"openblas-x64-bytes"
    (x64 / "lib" / "libscipy_openblas64_.dylib").write_bytes(openblas)
    (x64 / "lib" / "numpy" / ".dylibs" / "libscipy_openblas64_.dylib").write_bytes(
        openblas
    )
    (x64 / "lib" / "numpy" / ".dylibs" / "libgfortran.5.dylib").write_bytes(b"gfortran")
    wasm = x64 / "lib" / "wasmtime" / "darwin-x86_64" / "_libwasmtime.dylib"
    wasm.write_bytes(b"wasmtime-x64")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _unify_file_stub(bin_dir)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["MESHCHATX_UNIFY_ARM64_DIR"] = str(arm)
    env["MESHCHATX_UNIFY_X64_DIR"] = str(x64)
    result = subprocess.run(
        ["bash", str(_UNIFY)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (x64 / "lib" / "libscipy_openblas64_.dylib").read_bytes() == openblas
    assert (arm / "lib" / "libscipy_openblas64_.dylib").read_bytes() == openblas
    assert (
        arm / "lib" / "numpy" / ".dylibs" / "libscipy_openblas64_.dylib"
    ).read_bytes() == openblas
    assert (arm / "lib" / "numpy" / ".dylibs" / "libgfortran.5.dylib").read_bytes() == (
        b"gfortran"
    )
    assert not wasm.exists()
    assert "mirroring arch-only native" in result.stderr
    assert "dropping arch-only Mach-O" in result.stderr


def test_unify_errors_when_libcodec2_exists_on_only_one_arch(tmp_path: Path) -> None:
    arm = tmp_path / "arm"
    x64 = tmp_path / "x64"
    (arm / "lib").mkdir(parents=True)
    (x64 / "lib").mkdir(parents=True)
    (arm / "lib" / "libcodec2.dylib").write_bytes(b"codec2-arm")
    (arm / "readme.txt").write_text("same", encoding="utf-8")
    (x64 / "readme.txt").write_text("same", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _unify_file_stub(bin_dir)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["MESHCHATX_UNIFY_ARM64_DIR"] = str(arm)
    env["MESHCHATX_UNIFY_X64_DIR"] = str(x64)
    result = subprocess.run(
        ["bash", str(_UNIFY)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    assert "required native" in result.stderr
    assert "libcodec2.dylib" in result.stderr
