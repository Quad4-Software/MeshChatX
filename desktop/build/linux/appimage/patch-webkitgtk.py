#!/usr/bin/env python3
"""Patch a bundled libwebkitgtk-6.0.so.4 for AppImage use.

WebKitGTK 6.0 has no WEBKIT_EXEC_PATH-style override (verified empirically:
the env var is ignored and helpers are always spawned from the compiled-in
LIBEXECDIR). The library embeds the absolute helper directory, e.g.
"/usr/lib/webkitgtk-6.0", twice: once standalone (WebKitWebProcess,
WebKitNetworkProcess, WebKitGPUProcess) and once as the prefix of
"/usr/lib/webkitgtk-6.0/injected-bundle/".

This script rewrites every occurrence of ABS (the absolute helper dir,
NUL-terminated C string data) to REL, an equal-length relative path formed
by stripping the leading '/' and appending '/'. AppRun cd's into $APPDIR
before exec, so the relative path resolves to <AppDir>/<REL-without-slash>.
The injected-bundle path becomes e.g. "usr/lib/webkitgtk-6.0//injected-
bundle/" — the double slash is harmless for exec and dlopen.

The bwrap/xdg-dbus-proxy sandbox helper paths ("/usr/bin/...") are left
absolute on purpose: they are host binaries.

Usage: patch-webkitgtk.py <libwebkitgtk.so> <abs-helper-dir>
       e.g. patch-webkitgtk.py usr/lib/libwebkitgtk-6.0.so.4 /usr/lib/webkitgtk-6.0
Exits non-zero if the expected strings are not found or look unsafe.
"""

import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    path, absdir = sys.argv[1], sys.argv[2].encode()
    if not absdir.startswith(b"/") or absdir.endswith(b"/"):
        print(f"abs-helper-dir must be absolute without trailing slash: {absdir!r}")
        return 2
    # REL = absdir without leading '/', plus a trailing '/'. Same length.
    rel = absdir[1:] + b"/"
    assert len(rel) == len(absdir)

    data = bytearray(open(path, "rb").read())

    count = 0
    start = 0
    while True:
        i = data.find(absdir, start)
        if i < 0:
            break
        before = data[i - 1] if i > 0 else 0
        after_idx = i + len(absdir)
        after = data[after_idx] if after_idx < len(data) else 0
        # Must be C-string data: preceded by NUL (or start), followed by NUL
        # or '/' (the injected-bundle suffix). Refuse anything else.
        if before != 0:
            print(f"refusing to patch at offset {i}: preceding byte {before!r}")
            return 1
        if after not in (0, ord("/")):
            print(f"refusing to patch at offset {i}: following byte {after!r}")
            return 1
        data[i : i + len(absdir)] = rel
        count += 1
        start = i + len(rel)

    if count < 2:
        print(f"expected >=2 occurrences of {absdir!r}, found {count}; aborting")
        return 1

    open(path, "wb").write(data)
    print(f"patched {count} occurrence(s) of {absdir!r} -> {rel!r} in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
