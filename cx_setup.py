import sys
from pathlib import Path

from cx_Freeze import Executable, setup

from meshchatx.src.version import __version__

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "meshchatx" / "public"

include_files = [
    (str(PUBLIC_DIR), "public"),
    ("logo", "logo"),
]

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
            target_name="ReticulumMeshChatX",
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
            "build_exe": "build/exe",
            "replace_paths": [
                ("*", ""),
            ],
        },
    },
)
