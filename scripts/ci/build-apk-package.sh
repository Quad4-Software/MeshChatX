#!/usr/bin/env bash
# Assemble an apk-tools v2 package (Alpine .apk) without fpm.
#
# fpm's apk output produces packages apk-tools rejects: invalid tar
# header checksums, Debian arch names, missing datahash, bash-only
# install scripts, and no per-file APK-TOOLS.checksum.SHA1 records in
# the data member. This script writes the package directly:
# control.tar.gz (.PKGINFO + install scripts) then data.tar.gz.
# Unsigned packages install with apk --allow-untrusted.
#
# Usage:
#   build-apk-package.sh --from-unpacked dist/linux-unpacked
#   build-apk-package.sh --rootfs DIR
#
# Options:
#   --from-unpacked DIR   electron-builder dir output. Staged under
#                         opt/<productName>/ with usr/bin symlink,
#                         desktop file, and hicolor icon added
#   --rootfs DIR          pre-staged payload tree (paths relative to /)
#   --output FILE         output path (default: dist/<artifactName>)
#
# Env overrides: APK_NAME, APK_VERSION, APK_RELEASE (default r0),
# APK_ARCH (x86_64|aarch64), APK_PRODUCT, APK_DESCRIPTION, APK_URL,
# APK_MAINTAINER, APK_LICENSE, APK_DEPENDS (space separated)
set -euo pipefail

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

UNPACKED=""
ROOTFS=""
OUTPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --from-unpacked)
            UNPACKED="$2"
            shift 2
            ;;
        --rootfs)
            ROOTFS="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        *)
            echo "build-apk-package.sh: unknown arg $1" >&2
            exit 2
            ;;
    esac
done

pkg_json() {
    node -e "const p=require('./package.json');const path='$1'.split('.');let v=p;for(const k of path){v=v&&v[k]}console.log(v??'')"
}

APK_NAME="${APK_NAME:-$(pkg_json name)}"
APK_VERSION="${APK_VERSION:-$(pkg_json version)}"
APK_PRODUCT="${APK_PRODUCT:-$(pkg_json build.productName)}"
APK_RELEASE="${APK_RELEASE:-r0}"
APK_ARCH="${APK_ARCH:-x86_64}"
APK_DESCRIPTION="${APK_DESCRIPTION:-$(pkg_json description)}"
APK_URL="${APK_URL:-https://github.com/Quad4-Software/MeshChatX}"
APK_MAINTAINER="${APK_MAINTAINER:-Quad4}"
APK_LICENSE="${APK_LICENSE:-$(pkg_json license)}"

# Electron ships glibc binaries, so musl systems need gcompat plus the
# GTK/NSS/ALSA stack the deb declares. libxscrnsaver is Debian libxss1.
if [ -z "${APK_DEPENDS+x}" ]; then
    APK_DEPENDS="gcompat libstdc++ gtk+3.0 libnotify nss libxscrnsaver libxtst xdg-utils at-spi2-core libuuid libsecret"
fi

case "$APK_ARCH" in
    x64 | amd64) APK_ARCH="x86_64" ;;
    arm64) APK_ARCH="aarch64" ;;
esac

if [ -z "$APK_NAME" ] || [ -z "$APK_VERSION" ] || [ -z "$APK_PRODUCT" ]; then
    echo "build-apk-package.sh: could not read name/version/productName from package.json" >&2
    exit 1
fi

FILE_ARCH="x64"
case "$APK_ARCH" in
    aarch64) FILE_ARCH="arm64" ;;
esac

if [ -z "$OUTPUT" ]; then
    OUTPUT="dist/ReticulumMeshChatX-v${APK_VERSION}-linux-alpine-${FILE_ARCH}.apk"
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/apk-build.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT INT

stage_from_unpacked() {
    ROOTFS="$TMP/rootfs"
    mkdir -p "$ROOTFS/opt/$APK_PRODUCT" "$ROOTFS/usr/bin" \
        "$ROOTFS/usr/share/applications" \
        "$ROOTFS/usr/share/icons/hicolor/800x800/apps"

    cp -a "$UNPACKED/." "$ROOTFS/opt/$APK_PRODUCT/"

    ln -s "/opt/$APK_PRODUCT/$APK_NAME" "$ROOTFS/usr/bin/$APK_NAME"

    if [ -f packaging/arch/reticulum-meshchatx.desktop ]; then
        install -Dm644 packaging/arch/reticulum-meshchatx.desktop \
            "$ROOTFS/usr/share/applications/$APK_NAME.desktop"
    fi
    if [ -f electron/build/icon.png ]; then
        install -Dm644 electron/build/icon.png \
            "$ROOTFS/usr/share/icons/hicolor/800x800/apps/$APK_NAME.png"
    fi
}

if [ -n "$UNPACKED" ]; then
    [ -d "$UNPACKED" ] || {
        echo "build-apk-package.sh: unpacked dir missing: $UNPACKED" >&2
        exit 1
    }
    stage_from_unpacked
elif [ -z "$ROOTFS" ] || [ ! -d "$ROOTFS" ]; then
    echo "build-apk-package.sh: --rootfs DIR required (or --from-unpacked)" >&2
    exit 1
else
    # Pre-staged trees (for example a deb extract) may rely on maintainer
    # scripts for the bin symlink. Ship it in the payload instead.
    mkdir -p "$ROOTFS/usr/bin"
    if [ ! -e "$ROOTFS/usr/bin/$APK_NAME" ] && [ ! -L "$ROOTFS/usr/bin/$APK_NAME" ]; then
        _bin="$(find "$ROOTFS/opt" -maxdepth 2 -type f -name "$APK_NAME" -print -quit 2>/dev/null || true)"
        if [ -n "$_bin" ]; then
            ln -s "/${_bin#"$ROOTFS"/}" "$ROOTFS/usr/bin/$APK_NAME"
        fi
    fi
fi

# --- data member ---------------------------------------------------------
# apk-tools requires a pax extended header with
# APK-TOOLS.checksum.SHA1=<sha1 of file contents> on every regular file
# entry, so the data tar is written by python rather than GNU tar.

DATA="$TMP/data.tar.gz"
export APK_ROOTFS="$ROOTFS" APK_DATA_OUT="$TMP/data.tar"

python3 - <<'PYEOF'
import hashlib
import io
import os
import tarfile

rootfs = os.environ["APK_ROOTFS"]
out_path = os.environ["APK_DATA_OUT"]


def pax_records(tarinfo, data):
    records = "11 ctime=0\n11 atime=0\n"
    if data is not None:
        sha1 = hashlib.sha1(data).hexdigest()
        rec = f"APK-TOOLS.checksum.SHA1={sha1}\n"
        records = f"{len(rec) + 3} {rec}" + records
    return records.encode()


def add_checked(tar, tarinfo, data=None):
    body = pax_records(tarinfo, data)
    pax = tarfile.TarInfo()
    base = tarinfo.name.rstrip("/").split("/")[-1] or "entry"
    pax.name = "./PaxHeaders/" + base
    pax.type = tarfile.XHDTYPE
    pax.mode = 0o644
    pax.mtime = int(tarinfo.mtime)
    pax.size = len(body)
    tar.addfile(pax, io.BytesIO(body))
    tar.addfile(tarinfo, io.BytesIO(data) if data is not None else None)


entries = []
for dirpath, dirnames, filenames in os.walk(rootfs):
    dirnames.sort()
    filenames.sort()
    rel_dir = os.path.relpath(dirpath, rootfs)
    rel_dir = "" if rel_dir == "." else rel_dir
    for name in sorted(dirnames + filenames):
        full = os.path.join(dirpath, name)
        rel = os.path.join(rel_dir, name)
        if os.path.islink(full):
            entries.append((rel, "link"))
        elif os.path.isdir(full):
            entries.append((rel, "dir"))
        else:
            entries.append((rel, "file"))

with tarfile.open(out_path, "w:", format=tarfile.USTAR_FORMAT) as tar:
    for rel, kind in entries:
        full = os.path.join(rootfs, rel)
        st = os.lstat(full)
        info = tarfile.TarInfo()
        info.name = rel + ("/" if kind == "dir" else "")
        info.mode = st.st_mode & 0o7777
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = int(st.st_mtime)
        if kind == "dir":
            info.type = tarfile.DIRTYPE
            add_checked(tar, info)
        elif kind == "link":
            info.type = tarfile.SYMTYPE
            info.linkname = os.readlink(full)
            add_checked(tar, info, os.readlink(full).encode())
        else:
            info.type = tarfile.REGTYPE
            with open(full, "rb") as fh:
                data = fh.read()
            info.size = len(data)
            add_checked(tar, info, data)
PYEOF

python3 - "$TMP/data.tar" "$DATA" <<'PYEOF'
import gzip
import sys

src, dst = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read()
while raw.endswith(b"\0" * 512):
    raw = raw[: -512]
with open(dst, "wb") as fh:
    fh.write(gzip.compress(raw, compresslevel=9))
PYEOF
DATAHASH="$(sha256sum "$DATA" | cut -d' ' -f1)"
INSTALLED_SIZE="$(find "$ROOTFS" -type f -printf '%s\n' | awk '{s+=$1} END {print s+0}')"

# --- control member ------------------------------------------------------

CTRL="$TMP/control"
mkdir -p "$CTRL"

{
    echo "pkgname = $APK_NAME"
    echo "pkgver = ${APK_VERSION}-${APK_RELEASE}"
    echo "pkgdesc = $APK_DESCRIPTION"
    echo "url = $APK_URL"
    echo "builddate = $(date +%s)"
    if _sha="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)"; then
        echo "commit = $_sha"
    fi
    echo "size = $INSTALLED_SIZE"
    echo "arch = $APK_ARCH"
    echo "origin = $APK_NAME"
    echo "maintainer = $APK_MAINTAINER"
    echo "license = $APK_LICENSE"
    for dep in $APK_DEPENDS; do
        echo "depend = $dep"
    done
    echo "datahash = $DATAHASH"
} >"$CTRL/.PKGINFO"

cat >"$CTRL/.post-install" <<'EOS'
#!/bin/sh
# chrome-sandbox needs setuid root only when user namespaces are unavailable.
if ! { [ -e /proc/self/ns/user ] && unshare --user true 2>/dev/null; }; then
    chmod 4755 '/opt/Reticulum MeshChatX/chrome-sandbox' 2>/dev/null || true
else
    chmod 0755 '/opt/Reticulum MeshChatX/chrome-sandbox' 2>/dev/null || true
fi
if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database /usr/share/mime >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
exit 0
EOS

cat >"$CTRL/.post-deinstall" <<'EOS'
#!/bin/sh
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
exit 0
EOS

chmod 755 "$CTRL/.post-install" "$CTRL/.post-deinstall"

# The control member must match abuild's writer exactly: a pax extended
# header before each entry and no trailing end-of-archive padding. apk
# rejects members that carry extra bytes after the last file.
CTRL_TAR="$TMP/control.tar.gz"
export APK_CTRL_DIR="$CTRL" APK_CTRL_OUT="$CTRL_TAR"

python3 - <<'PYEOF'
import gzip
import io
import os
import tarfile

ctrl = os.environ["APK_CTRL_DIR"]
out_path = os.environ["APK_CTRL_OUT"]

buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:", format=tarfile.USTAR_FORMAT) as tar:
    for name in (".PKGINFO", ".pre-install", ".post-install",
                 ".pre-upgrade", ".post-upgrade",
                 ".pre-deinstall", ".post-deinstall"):
        path = os.path.join(ctrl, name)
        if not os.path.isfile(path):
            continue
        data = open(path, "rb").read()
        pax_body = b"11 ctime=0\n11 atime=0\n"
        pax = tarfile.TarInfo("./PaxHeaders/" + name)
        pax.type = tarfile.XHDTYPE
        pax.mode = 0o644
        pax.size = len(pax_body)
        tar.addfile(pax, io.BytesIO(pax_body))
        info = tarfile.TarInfo(name)
        info.mode = 0o755 if name != ".PKGINFO" else 0o644
        info.mtime = 0
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

raw = buf.getvalue()
while raw.endswith(b"\0" * 512):
    raw = raw[: -512]
with open(out_path, "wb") as fh:
    fh.write(gzip.compress(raw))
PYEOF

# --- final package: control member then data member ----------------------

mkdir -p "$(dirname "$OUTPUT")"
cat "$CTRL_TAR" "$DATA" >"$OUTPUT"

echo "build-apk-package.sh: wrote $OUTPUT"
echo "  pkgname=$APK_NAME pkgver=${APK_VERSION}-${APK_RELEASE} arch=$APK_ARCH size=$INSTALLED_SIZE"
