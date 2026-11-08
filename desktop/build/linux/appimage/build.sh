#!/usr/bin/env bash
# AppImage assembly for MeshChatX (Wails v3 shell + bundled backend).
#
# Stages an AppDir, runs linuxdeploy with the GTK4 and GStreamer plugins,
# patches the bundled libwebkitgtk-6.0.so.4 helper paths (WebKitGTK 6.0 has
# no WEBKIT_EXEC_PATH override — see patch-webkitgtk.py), fixes helper
# RPATHs, and packs with appimagetool.
#
# Inputs (env):
#   APP_NAME      binary/base name            (default: meshchatx-desktop)
#   APP_BINARY    path to the shell binary    (required)
#   BACKEND_DIR   dir with ReticulumMeshChatX (default: <desktop>/bin/backend)
#   ICON          512x512-ish PNG icon        (default: <desktop>/build/appicon.png)
#   VERSION       app version for output name (default: app-version.json)
#   ARCH          amd64|arm64|x64|aarch64     (default: amd64; arm64 untested)
#   OUT_DIR       output directory            (default: <desktop>/bin)
#   WORK_DIR      scratch dir                 (default: <desktop>/bin/appimage-work)
#   ALLOW_UNPINNED_TOOLS=1  permit "-" sha256 entries in tools.tsv
#
# Requires: bash, curl, pkg-config, python3, and a webkitgtk-6.0 + gtk4 +
# gstreamer-1.0 development install on the build host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"   # desktop/build/linux/appimage -> desktop
REPO_DIR="$(cd "$DESKTOP_DIR/.." && pwd)"

APP_NAME="${APP_NAME:-meshchatx-desktop}"
APP_BINARY="${APP_BINARY:-}"
BACKEND_DIR="${BACKEND_DIR:-$DESKTOP_DIR/bin/backend}"
ICON="${ICON:-$DESKTOP_DIR/build/appicon.png}"
OUT_DIR="${OUT_DIR:-$DESKTOP_DIR/bin}"
WORK_DIR="${WORK_DIR:-$DESKTOP_DIR/bin/appimage-work}"
case "${ARCH:-amd64}" in
    amd64|x64)        ARCH=amd64; TOOL_ARCH=x86_64; ARCH_SUFFIX=x64 ;;
    arm64|aarch64)    ARCH=arm64; TOOL_ARCH=aarch64; ARCH_SUFFIX=arm64 ;;
    *) echo "unsupported ARCH: ${ARCH:-}" >&2; exit 2 ;;
esac
if [ "$ARCH" = arm64 ]; then
    echo "WARNING: arm64 AppImage path is parameterized but NOT tested on this host." >&2
fi
if [ -z "$APP_BINARY" ]; then
    APP_BINARY="$DESKTOP_DIR/bin/$APP_NAME"
fi
VERSION="${VERSION:-}"
if [ -z "$VERSION" ]; then
    VERSION="$(python3 -c "import json;print(json.load(open('$DESKTOP_DIR/app-version.json'))['version'])" 2>/dev/null || true)"
fi
VERSION="${VERSION:-0.0.0}"

CACHE_DIR="$WORK_DIR/cache"
TOOLS_DIR="$WORK_DIR/tools"
TMP_WORK="$WORK_DIR/tmp"
APPDIR_PARENT="$WORK_DIR/AppDir"
APPDIR_NAME="${APP_NAME}.AppDir"
APPDIR="$APPDIR_PARENT/$APPDIR_NAME"
FINAL_NAME="ReticulumMeshChatX-v${VERSION}-linux-${ARCH_SUFFIX}.AppImage"

mkdir -p "$CACHE_DIR" "$TOOLS_DIR" "$TMP_WORK" "$OUT_DIR" "$APPDIR_PARENT"
export TMPDIR="$TMP_WORK"

log() { printf '\033[1;34m[appimage]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[appimage] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- tools ----

fetch_tools() {
    local tsv="$SCRIPT_DIR/tools.tsv"
    [ -f "$tsv" ] || die "tools.tsv missing at $tsv"
    local name kind url sha file dest
    while IFS=$'\t' read -r name kind url_x url_a sha_x sha_a; do
        [ -z "${name:-}" ] && continue
        case "$name" in \#*) continue;; esac
        local url sha
        if [ "$TOOL_ARCH" = x86_64 ]; then url="$url_x"; sha="$sha_x";
        else url="$url_a"; sha="$sha_a"; fi
        [ "$url" = "-" ] && { log "skipping $name (no $TOOL_ARCH url)"; continue; }
        file="$CACHE_DIR/$(basename "$url")"
        dest="$TOOLS_DIR/$name"
        if [ ! -f "$file" ]; then
            log "downloading $name <- $url"
            curl -fL --retry 3 --connect-timeout 20 -o "$file" "$url" \
                || die "download failed: $url"
        fi
        if [ "$sha" = "-" ] || [ -z "$sha" ]; then
            [ "${ALLOW_UNPINNED_TOOLS:-0}" = "1" ] \
                || die "no pinned sha256 for $name ($TOOL_ARCH); set ALLOW_UNPINNED_TOOLS=1 to override"
            log "WARNING: $name is unpinned for $TOOL_ARCH"
        else
            local got
            got="$(sha256sum "$file" | awk '{print $1}')"
            [ "$got" = "$sha" ] || die "sha256 mismatch for $name: got $got want $sha (delete $file to re-fetch)"
        fi
        case "$kind" in
            file|script)
                cp -f "$file" "$dest"
                chmod +x "$dest"
                ;;
            tarball)
                mkdir -p "$TOOLS_DIR/$name.d"
                tar -xzf "$file" -C "$TOOLS_DIR/$name.d"
                # patchelf tarballs ship bin/patchelf
                if [ -f "$TOOLS_DIR/$name.d/bin/$name" ]; then
                    cp -f "$TOOLS_DIR/$name.d/bin/$name" "$dest"
                elif [ -f "$TOOLS_DIR/$name.d/$name" ]; then
                    cp -f "$TOOLS_DIR/$name.d/$name" "$dest"
                else
                    die "tarball $name did not contain bin/$name"
                fi
                chmod +x "$dest"
                rm -rf "$TOOLS_DIR/$name.d"
                ;;
            *) die "unknown tool kind '$kind' for $name" ;;
        esac
    done < "$tsv"
}

# ------------------------------------------------------------- staging ----

stage_appdir() {
    log "staging AppDir at $APPDIR"
    rm -rf "$APPDIR"
    mkdir -p \
        "$APPDIR/usr/bin" \
        "$APPDIR/usr/lib/reticulum-meshchatx/backend" \
        "$APPDIR/usr/share/icons/hicolor/512x512/apps" \
        "$APPDIR/usr/share/metainfo"

    [ -f "$APP_BINARY" ] || die "APP_BINARY not found: $APP_BINARY"
    cp "$APP_BINARY" "$APPDIR/usr/bin/$APP_NAME"
    chmod 755 "$APPDIR/usr/bin/$APP_NAME"

    [ -d "$BACKEND_DIR" ] || die "BACKEND_DIR not found: $BACKEND_DIR"
    cp -a "$BACKEND_DIR/." "$APPDIR/usr/lib/reticulum-meshchatx/backend/"
    [ -f "$APPDIR/usr/lib/reticulum-meshchatx/backend/ReticulumMeshChatX" ] \
        || die "BACKEND_DIR lacks ReticulumMeshChatX executable"

    cp "$SCRIPT_DIR/AppRun" "$APPDIR/AppRun"
    chmod 755 "$APPDIR/AppRun"

    # linuxdeploy auto-reads <AppDir>/excludelist (one glob per line).
    cp "$SCRIPT_DIR/excludelist.txt" "$APPDIR/excludelist"

    # .desktop entry (validated by appimagetool / desktop-file-validate).
    cat > "$APPDIR/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Reticulum MeshChatX
GenericName=Mesh Network Chat Client
Comment=Local-first mesh communications on the Reticulum Network Stack
Exec=$APP_NAME %u
Icon=com.meshchatx.app
Terminal=false
Categories=Network;InstantMessaging;
MimeType=x-scheme-handler/lxmf;x-scheme-handler/rns;
Keywords=reticulum;mesh;lxmf;rns;chat;
StartupNotify=true
StartupWMClass=$APP_NAME
Version=1.0
EOF

    [ -f "$ICON" ] || die "ICON not found: $ICON"
    cp "$ICON" "$APPDIR/com.meshchatx.app.png"
    cp "$ICON" "$APPDIR/usr/share/icons/hicolor/512x512/apps/com.meshchatx.app.png"

    local metainfo="$REPO_DIR/packaging/flatpak/com.meshchatx.app.metainfo.xml"
    [ -f "$metainfo" ] || die "metainfo not found: $metainfo"
    sed "s|com.meshchatx.app.desktop|$APP_NAME.desktop|g" "$metainfo" \
        > "$APPDIR/usr/share/metainfo/com.meshchatx.app.metainfo.xml"

    stage_webkitgtk
    stage_gio_modules
    stage_gstreamer
    stage_pixbuf_cache_dir
}

# The gtk plugin regenerates loaders.cache inside the AppDir even when the
# host has no loaders dir; pre-create the parent so the redirect succeeds.
stage_pixbuf_cache_dir() {
    local cache
    cache="$(pkg-config --variable=gdk_pixbuf_cache_file gdk-pixbuf-2.0 2>/dev/null || true)"
    [ -n "$cache" ] || return 0
    mkdir -p "$APPDIR/$(dirname "${cache#/}")"
}

# Locate the host webkitgtk helper dir + copy the process helpers.
# pkg-config libdir on Arch is /usr/lib; Debian multiarch yields
# /usr/lib/<triplet> — the AppDir mirrors the same relative layout.
stage_webkitgtk() {
    local wk_libdir wk_rel
    wk_libdir="$(pkg-config --variable=libdir webkitgtk-6.0 2>/dev/null || true)"
    [ -n "$wk_libdir" ] || die "pkg-config webkitgtk-6.0 libdir not found"
    wk_rel="${wk_libdir#/}/webkitgtk-6.0"   # e.g. usr/lib/webkitgtk-6.0
    local src="$wk_libdir/webkitgtk-6.0"
    [ -d "$src" ] || die "webkitgtk helper dir not found: $src"
    mkdir -p "$APPDIR/$wk_rel"
    # Process helpers + jsc + injected bundle. MiniBrowser is a demo app — skip.
    for f in WebKitWebProcess WebKitNetworkProcess WebKitGPUProcess jsc; do
        [ -f "$src/$f" ] && cp -a "$src/$f" "$APPDIR/$wk_rel/$f"
    done
    [ -d "$src/injected-bundle" ] && cp -a "$src/injected-bundle" "$APPDIR/$wk_rel/"
    [ -f "$APPDIR/$wk_rel/WebKitWebProcess" ] || die "failed to stage WebKit helpers"
    WK_APPDIR_REL="$wk_rel"   # e.g. usr/lib/webkitgtk-6.0 (may be multiarch)
    # The absolute path embedded in libwebkitgtk (e.g. /usr/lib/webkitgtk-6.0)
    # is what patch-webkitgtk.py rewrites after linuxdeploy copies the lib.
    echo "$wk_libdir/webkitgtk-6.0" > "$APPDIR_PARENT/.webkit-absdir"
}

# glib-networking (TLS for libsoup inside WebKit) and other GIO modules.
stage_gio_modules() {
    local gio_libdir mods
    gio_libdir="$(pkg-config --variable=libdir gio-2.0 2>/dev/null || echo /usr/lib)"
    mods="$gio_libdir/gio/modules"
    [ -d "$mods" ] || { log "no gio modules dir at $mods — skipping"; return 0; }
    mkdir -p "$APPDIR/usr/lib/gio/modules"
    # Copy .so files only: giomodule.cache holds absolute host paths.
    find "$mods" -maxdepth 1 -name '*.so' -exec cp -a {} "$APPDIR/usr/lib/gio/modules/" \;
    if [ -z "$(ls -A "$APPDIR/usr/lib/gio/modules" 2>/dev/null)" ]; then
        rmdir "$APPDIR/usr/lib/gio/modules" "$APPDIR/usr/lib/gio" 2>/dev/null || true
    fi
}

# GStreamer plugin modules WebKit uses for media playback (app, playback,
# coreelements, typefind, audio/video convert, isomp4, ...). The host may
# lack sink plugins (pulsesink/pipewire); that only affects audible output.
stage_gstreamer() {
    local gst_dir
    gst_dir="$(pkg-config --variable=pluginsdir gstreamer-1.0 2>/dev/null || true)"
    [ -n "$gst_dir" ] || gst_dir="/usr/lib/gstreamer-1.0"
    [ -d "$gst_dir" ] || { log "no gstreamer plugin dir at $gst_dir — skipping"; return 0; }
    mkdir -p "$APPDIR/usr/lib/gstreamer-1.0"
    # Plugin modules + the scanner/ptp helpers (arch binaries, small).
    find "$gst_dir" -maxdepth 1 -name 'libgst*.so' -exec cp -a {} "$APPDIR/usr/lib/gstreamer-1.0/" \;
    for helper in gst-plugin-scanner gst-ptp-helper; do
        [ -f "$gst_dir/$helper" ] && cp -a "$gst_dir/$helper" "$APPDIR/usr/lib/gstreamer-1.0/"
    done
}

# ------------------------------------------------------------- deploy ------

deploy() {
    log "running linuxdeploy + plugins (GTK4, GStreamer)"
    export PATH="$TOOLS_DIR:$PATH"
    # Some distros (e.g. Arch) ship no gtk-4.0 module dir and no gdk-pixbuf
    # loaders dir (loaders are built into libgdk_pixbuf). Make those copies
    # conditional — no-op where the dirs exist.
    local gtk_plugin="$TOOLS_DIR/linuxdeploy-plugin-gtk"
    if [ -f "$gtk_plugin" ]; then
        sed -i \
            -e 's|^\(\s*\)copy_lib_tree "\$gtk4_libdir" "\$APPDIR/"|\1[ ! -d "$gtk4_libdir" ] \|\| copy_lib_tree "$gtk4_libdir" "$APPDIR/"|' \
            -e 's|^\(\s*\)copy_lib_tree "\$gdk_pixbuf_binarydir" "\$APPDIR/"|\1[ ! -d "$gdk_pixbuf_binarydir" ] \|\| copy_lib_tree "$gdk_pixbuf_binarydir" "$APPDIR/"|' \
            "$gtk_plugin" || log "WARNING: could not patch gtk plugin for optional module dirs"
    fi
    local -a extra_exes=()
    local f
    for f in WebKitWebProcess WebKitNetworkProcess WebKitGPUProcess jsc; do
        [ -f "$APPDIR/$WK_APPDIR_REL/$f" ] && extra_exes+=(--executable "$APPDIR/$WK_APPDIR_REL/$f")
    done
    DEPLOY_GTK_VERSION=4 \
        "$TOOLS_DIR/linuxdeploy" \
            --appdir "$APPDIR" \
            --verbosity=1 \
            --plugin gtk \
            --plugin gstreamer \
            "${extra_exes[@]}" \
        || die "linuxdeploy failed"
}

post_deploy() {
    log "patching webkitgtk helper paths"
    local wk_abs wk_lib
    wk_abs="$(cat "$APPDIR_PARENT/.webkit-absdir")"
    wk_lib="$(find "$APPDIR" -name 'libwebkitgtk-6.0.so.4' -type f | head -1)"
    [ -n "$wk_lib" ] || die "bundled libwebkitgtk-6.0.so.4 not found"
    python3 "$SCRIPT_DIR/patch-webkitgtk.py" "$wk_lib" "$wk_abs"

    log "fixing helper RPATHs"
    local helperdir="$APPDIR/$WK_APPDIR_REL"
    if [ -d "$helperdir" ]; then
        # helpers live in <appdir>/<wk_rel> (e.g. usr/lib/webkitgtk-6.0);
        # bundled libs live in <appdir>/usr/lib — $ORIGIN/.. reaches them.
        # Preserve any rpath linuxdeploy already set by prepending.
        local h old new
        for h in WebKitWebProcess WebKitNetworkProcess WebKitGPUProcess jsc; do
            [ -f "$helperdir/$h" ] || continue
            old="$("$TOOLS_DIR/patchelf" --print-rpath "$helperdir/$h" 2>/dev/null || true)"
            case ":$old:" in
                *':$ORIGIN/..:'*|*'$ORIGIN/..'*) new="$old" ;;
                *) [ -n "$old" ] && new='$ORIGIN/..:'"$old" || new='$ORIGIN/..' ;;
            esac
            "$TOOLS_DIR/patchelf" --set-rpath "$new" "$helperdir/$h" \
                || log "WARNING: patchelf rpath failed for $h"
        done
        local inj="$helperdir/injected-bundle/libwebkitgtkinjectedbundle.so"
        if [ -f "$inj" ]; then
            old="$("$TOOLS_DIR/patchelf" --print-rpath "$inj" 2>/dev/null || true)"
            case ":$old:" in
                *':$ORIGIN/../..:'*|*'$ORIGIN/../..'*) new="$old" ;;
                *) [ -n "$old" ] && new='$ORIGIN/../..:'"$old" || new='$ORIGIN/../..' ;;
            esac
            "$TOOLS_DIR/patchelf" --set-rpath "$new" "$inj" \
                || log "WARNING: patchelf rpath failed for injected bundle"
        fi
    else
        log "WARNING: helper dir $helperdir missing — skipping rpath fix"
    fi
}

# GStreamer plugins are copied from the BUILD HOST's plugin set, so a host
# without gst-plugins-good/-bad/-ugly produces an AppImage whose embedded
# browser cannot play audio or decode most media. Warn loudly; install the
# plugin packages on the build host for a complete bundle.
check_gst_plugins() {
    local gst_dir="$APPDIR/usr/lib/gstreamer-1.0"
    [ -d "$gst_dir" ] || { log "WARNING: no bundled gstreamer plugin dir at $gst_dir"; return; }
    local missing=()
    local -a groups=(
        "audio-sink|libgstpulse|libgstpipewire|libgstalsa"
        "http-source|libsouphttpsrc"
        "av-codecs|libgstlibav|libgstopenh264|libgstmpeg2dec|libgstx264"
        "common-decoder|libgstopus|libgstvpx|libgstvorbisd|libgsttheora|libgstjpeg|libgstpng|libgstaudioparsers|libgstplayback|libgstencoding"
    )
    local g label pat found
    for g in "${groups[@]}"; do
        label="${g%%|*}"; pat="${g#*|}"
        found=0
        local p
        for p in "$gst_dir"/*.so; do
            [ -e "$p" ] || continue
            if [[ "$(basename "$p")" =~ $pat ]]; then found=1; break; fi
        done
        [ $found -eq 0 ] && missing+=("$label")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log "WARNING: bundled GStreamer plugins lack: ${missing[*]}"
        log "WARNING: install gst-plugins-base/good/bad/ugly (+gst-libav) on the"
        log "WARNING: build host and rebuild for full in-page media playback."
        log "WARNING: this AppImage will run but WebKitGTK audio/media will fail."
    else
        log "gstreamer plugin coverage looks complete"
    fi
}

pack() {
    log "packing AppImage with appimagetool"
    export ARCH="$TOOL_ARCH"
    local out="$WORK_DIR/out"
    rm -rf "$out"; mkdir -p "$out"
    (cd "$out" && "$TOOLS_DIR/appimagetool" "$APPDIR") \
        || die "appimagetool failed"
    local produced
    produced="$(find "$out" -maxdepth 1 -name '*.AppImage' | head -1)"
    [ -n "$produced" ] || die "appimagetool produced no AppImage in $out"
    mv "$produced" "$OUT_DIR/$FINAL_NAME"
    chmod +x "$OUT_DIR/$FINAL_NAME"
    log "wrote $OUT_DIR/$FINAL_NAME"
    ls -la "$OUT_DIR/$FINAL_NAME"
    sha256sum "$OUT_DIR/$FINAL_NAME"
}

main() {
    fetch_tools
    stage_appdir
    deploy
    post_deploy
    check_gst_plugins
    pack
}

main "$@"
