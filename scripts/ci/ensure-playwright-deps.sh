#!/usr/bin/env bash
# Provision the shared libraries Playwright's bundled Chromium needs on
# self-hosted runners where `playwright install --with-deps` cannot run
# (non-Debian, no root). Fetches the Arch packages into a dedicated
# $HOME dir and exports LD_LIBRARY_PATH for later steps.
#
# No-op when the system already provides the key libraries.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/user-space-pkgs.sh
. "$(dirname "$0")/user-space-pkgs.sh"

# Skip when the host already ships a working set (e.g. a desktop Arch
# install). libnspr4 + libnss3 + libgbm are representative canaries.
if ldconfig -p 2>/dev/null | grep -q 'libnspr4\.so' \
    && ldconfig -p 2>/dev/null | grep -q 'libnss3\.so' \
    && ldconfig -p 2>/dev/null | grep -q 'libgbm\.so'; then
    echo "ensure-playwright-deps: system already provides Chromium libs"
    exit 0
fi

export MESHCHAT_SYSLIBS_DEST="$HOME/.local/meshchatx-ci/browserlibs"

# Runtime deps of chrome-headless-shell on Arch, derived from the binary's
# own NEEDED list (superset of the Debian --with-deps list; extra libs are
# harmless and fetch failures only warn). atk merged into at-spi2-core,
# and the cups client library split into libcups. ttf-dejavu provides the
# fonts Skia's fontconfig fallback needs (see below).
PKGS="nspr nss at-spi2-core atk libcups libdrm libxkbcommon libxcomposite \
libxdamage libxfixes libxrandr libxext libxrender libxi libxtst libx11 \
libxcb libxau libxdmcp libxshmfence libxxf86vm libxt libxft fontconfig \
freetype2 cairo pango glib2 expat alsa-lib mesa libglvnd libpng \
libjpeg-turbo libwebp harfbuzz graphite fribidi libdatrie libthai \
libepoxy wayland libffi util-linux-libs dbus systemd-libs pcre2 zlib \
gcc-libs ttf-dejavu"

for pkg in ${PKGS}; do
    fetch_arch_pkg "${pkg}" || echo "ensure-playwright-deps: ${pkg} unavailable" >&2
done

# Chromium's Skia font fallback aborts the renderer with
# FATAL SkFontMgr_FontConfigInterface "Not implemented" when fontconfig
# finds no config file or no fonts, which kills the page mid-test on
# minimal hosts. Give fontconfig a user-space config that scans the font
# dirs shipped by the fetched packages plus the usual system dirs, and
# link the stock conf.default fragments the way the Arch package install
# would have.
FONTCONFIG_DIR="${HOME}/.local/meshchatx-ci/fontconfig"
FC_CONF_SRC="${MESHCHAT_SYSLIBS_DEST}/etc/fonts/fonts.conf"
if [[ -f "${FC_CONF_SRC}" ]]; then
    mkdir -p "${FONTCONFIG_DIR}/conf.d"
    cp "${FC_CONF_SRC}" "${FONTCONFIG_DIR}/fonts.conf"
    # Point fontconfig at the extracted font dir and drop the system cache
    # dir, which is not writable for the runner user.
    sed -i \
        -e "s|<dir>/usr/share/fonts</dir>|<dir>/usr/share/fonts</dir>\n\t<dir>${MESHCHAT_SYSLIBS_DEST}/usr/share/fonts</dir>|" \
        -e '/<cachedir>\/var\/cache\/fontconfig<\/cachedir>/d' \
        -e "0,/<cachedir/s||<cachedir>${FONTCONFIG_DIR}/cache</cachedir>\n\t<cachedir|" \
        "${FONTCONFIG_DIR}/fonts.conf"
    mkdir -p "${FONTCONFIG_DIR}/cache"
    for frag in "${MESHCHAT_SYSLIBS_DEST}/usr/share/fontconfig/conf.default"/*.conf; do
        [[ -e "${frag}" ]] || continue
        ln -sf "${frag}" "${FONTCONFIG_DIR}/conf.d/$(basename "${frag}")"
    done
    export FONTCONFIG_FILE="${FONTCONFIG_DIR}/fonts.conf"
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        echo "FONTCONFIG_FILE=${FONTCONFIG_FILE}" >> "${GITHUB_ENV}"
    fi
else
    echo "ensure-playwright-deps: fontconfig package missing, skipping font config" >&2
fi

LIBDIR="${MESHCHAT_SYSLIBS_DEST}/usr/lib"
if [[ -d "${LIBDIR}" ]]; then
    export LD_LIBRARY_PATH="${LIBDIR}:${LD_LIBRARY_PATH:-}"
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" >> "$GITHUB_ENV"
    fi
fi

# Report which of the canary libs are still missing.
missing=0
for lib in libnspr4.so libnss3.so libgbm.so libasound.so libcups.so; do
    if ! ldconfig -p 2>/dev/null | grep -q "${lib}" \
        && ! compgen -G "${LIBDIR}/${lib}*" >/dev/null; then
        echo "ensure-playwright-deps: still missing ${lib}" >&2
        missing=1
    fi
done
exit "${missing}"
