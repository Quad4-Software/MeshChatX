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

# Runtime deps of chrome-headless-shell on Arch (superset of the Debian
# --with-deps list; extra libs are harmless). atk merged into
# at-spi2-core, and the cups client library split into libcups.
PKGS="nspr nss at-spi2-core libcups libdrm libxkbcommon libxcomposite \
libxdamage libxfixes libxrandr libxext libxrender libxi libxtst libx11 \
libxcb libxshmfence libxxf86vm libxt libxft fontconfig freetype2 cairo \
pango glib2 expat alsa-lib mesa libglvnd libpng libjpeg-turbo libwebp \
harfbuzz graphite fribidi libdatrie libthai libepoxy wayland"

for pkg in ${PKGS}; do
    fetch_arch_pkg "${pkg}" || echo "ensure-playwright-deps: ${pkg} unavailable" >&2
done

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
