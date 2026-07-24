# SPDX-License-Identifier: 0BSD

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_vendor_lxmfy = ROOT / "vendor" / "lxmfy"
if _vendor_lxmfy.is_dir() and (_vendor_lxmfy / "lxmfy").is_dir():
    sys.path.insert(0, str(_vendor_lxmfy))
_vendor_rns_filesync = ROOT / "vendor" / "rns_filesync"
if _vendor_rns_filesync.is_dir() and (_vendor_rns_filesync / "rns_filesync").is_dir():
    sys.path.insert(0, str(_vendor_rns_filesync))

from cx_Freeze import Executable, setup  # noqa: E402

from meshchatx.src.version import __version__  # noqa: E402

PUBLIC_DIR = ROOT / "meshchatx" / "public"

target_name = os.environ.get("CX_FREEZE_TARGET_NAME", "ReticulumMeshChatX")
build_exe_dir = os.environ.get("CX_FREEZE_BUILD_EXE", "build/exe")

include_files = []

changelog_path = ROOT / "CHANGELOG.md"
if changelog_path.exists():
    include_files.append((str(changelog_path), "CHANGELOG.md"))

frontend_licenses_path = (
    ROOT / "meshchatx" / "src" / "backend" / "data" / "licenses_frontend.json"
)
if frontend_licenses_path.exists():
    include_files.append((str(frontend_licenses_path), "licenses_frontend.json"))

backend_licenses_path = (
    ROOT / "meshchatx" / "src" / "backend" / "data" / "licenses_backend.json"
)
if backend_licenses_path.exists():
    include_files.append((str(backend_licenses_path), "licenses_backend.json"))

third_party_notices_path = (
    ROOT / "meshchatx" / "src" / "backend" / "data" / "THIRD_PARTY_NOTICES.txt"
)
if third_party_notices_path.exists():
    include_files.append((str(third_party_notices_path), "THIRD_PARTY_NOTICES.txt"))

if PUBLIC_DIR.exists() and PUBLIC_DIR.is_dir():
    include_files.append((str(PUBLIC_DIR), "public"))

logo_dir = ROOT / "logo"
if logo_dir.exists() and logo_dir.is_dir():
    include_files.append(("logo", "logo"))

bin_dir = ROOT / "bin"
if bin_dir.exists() and bin_dir.is_dir():
    include_files.append(("bin", "bin"))

packages = [
    "RNS",
    "RNS.Interfaces",
    "LXMF",
    "LXST",
    "lxmfy",
    "rns_filesync",
    "websockets",
    "pycparser",
    "cffi",
    "ply",
    "bleak",
]

# Keep FS sandbox helpers even when import tracing is incomplete (Windows
# launcher is entered via --meshchatx-run-module and must stay in the freeze).
includes = [
    "meshchatx.src.backend.landlock_sandbox",
    "meshchatx.src.backend.appcontainer_sandbox",
    "meshchatx.src.backend.appcontainer_launcher",
    "meshchatx.src.backend.seccomp_sandbox",
]

if sys.version_info >= (3, 13):
    packages.append("audioop")

setup(
    name="ReticulumMeshChatX",
    version=__version__,
    description="A simple mesh network communications app powered by the Reticulum Network Stack",
    executables=[
        Executable(
            script="meshchatx/meshchat.py",
            base=None,
            target_name=target_name,
            shortcut_name="ReticulumMeshChatX",
            shortcut_dir="ProgramMenuFolder",
            icon="logo/icon.ico",
        ),
    ],
    options={
        "build_exe": {
            "packages": packages,
            "includes": includes,
            "include_files": include_files,
            "excludes": [
                "PIL",
                "tkinter",
                "pydoc",
                "pydoc_data",
                "setuptools",
                "distutils",
                "pkg_resources",
            ],
            "optimize": 2,
            "build_exe": build_exe_dir,
            "replace_paths": [
                ("*", ""),
            ],
        },
    },
)
