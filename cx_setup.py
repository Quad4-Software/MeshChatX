import os
import sys
from pathlib import Path

from cx_Freeze import Executable, setup

from meshchatx.src.version import __version__

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "meshchatx" / "public"

target_name = os.environ.get("CX_FREEZE_TARGET_NAME", "ReticulumMeshChatX")
build_exe_dir = os.environ.get("CX_FREEZE_BUILD_EXE", "build/exe")

include_files = []

changelog_path = ROOT / "CHANGELOG.md"
if changelog_path.exists():
    include_files.append((str(changelog_path), "CHANGELOG.md"))

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
    "pycparser",
    "cffi",
    "ply",
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
            "include_files": include_files,
            "excludes": [
                "PIL",
            ],
            "optimize": 1,
            "build_exe": build_exe_dir,
            "replace_paths": [
                ("*", ""),
            ],
        },
    },
)
