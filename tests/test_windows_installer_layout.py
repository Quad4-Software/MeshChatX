# SPDX-License-Identifier: 0BSD

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "ci"))

from check_windows_installer_layout import check_listing

GOOD_LISTING = [
    "$INSTDIR/meshchatx-desktop.exe",
    "$INSTDIR/backend/ReticulumMeshChatX.exe",
    "$INSTDIR/backend/lib/python313.dll",
    "$INSTDIR/backend/lib/library.zip",
    "$INSTDIR/uninstall.exe",
]


def test_good_listing_passes():
    assert check_listing(GOOD_LISTING) == []


def test_stranded_root_listing_fails():
    stranded = [
        "$INSTDIR/meshchatx-desktop.exe",
        "$INSTDIR/ReticulumMeshChatX.exe",
        "$INSTDIR/lib/python313.dll",
        "$INSTDIR/backend/",
    ]
    errors = check_listing(stranded)
    assert any("stranded" in e for e in errors)
    assert any("backend/reticulummeshchatx.exe" in e for e in errors)
    assert any("backend/lib/" in e for e in errors)


def test_missing_shell_exe_fails():
    listing = [p for p in GOOD_LISTING if "meshchatx-desktop.exe" not in p]
    errors = check_listing(listing)
    assert any("meshchatx-desktop.exe" in e for e in errors)


def test_backslashes_and_case_normalized():
    listing = [
        "$INSTDIR\\MESHCHATX-DESKTOP.EXE",
        "$INSTDIR\\BACKEND\\RETICULUMMESHCHATX.EXE",
        "$INSTDIR\\Backend\\LIB\\python313.dll",
    ]
    assert check_listing(listing) == []


def test_instdir_prefix_stripped_and_pluginsdir_ignored():
    listing = [
        "$PLUGINSDIR/ReticulumMeshChatX.exe",
        "$PLUGINSDIR/webview2bootstrapper/MicrosoftEdgeWebview2Setup.exe",
        "$_OUTDIR/meshchatx-desktop.exe",
        "$_OUTDIR/backend/ReticulumMeshChatX.exe",
        "$_OUTDIR/backend/lib/library.zip",
    ]
    assert check_listing(listing) == []


def test_pluginsdir_stranded_exe_does_not_trigger():
    listing = [*GOOD_LISTING, "$PLUGINSDIR/ReticulumMeshChatX.exe"]
    assert check_listing(listing) == []
