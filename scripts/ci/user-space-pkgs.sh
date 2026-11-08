# shellcheck shell=bash
# User-space package fetching for self-hosted runners without root.
# Sourced by github-install-deps.sh and ensure-user-tools.sh.
#
# fetch_arch_pkg downloads Arch packages (via pacman download-only or the
# package API + geo mirror) and extracts them into
# $HOME/.local/meshchatx-ci/syslibs. link_syslib_bins puts binaries found
# under syslibs/usr/bin on PATH via ~/.local/bin.

fetch_arch_pkg() {
    local pkg="$1"
    local dest="$HOME/.local/meshchatx-ci/syslibs"
    mkdir -p "${dest}/pkgs"
    local f url tmp
    if command -v pacman >/dev/null 2>&1; then
        pacman -Sw --cachedir "${dest}/pkgs" --noconfirm "${pkg}" >/dev/null 2>&1 || true
    fi
    if ! compgen -G "${dest}/pkgs/${pkg}-*.pkg.tar.zst" >/dev/null; then
        # Package search API: pick the result whose pkgname matches
        # exactly and take its authoritative filename + repo.
        local row fname rep
        row="$(curl -fsSL --max-time 30 \
            "https://archlinux.org/packages/search/json/?name=${pkg}" 2>/dev/null \
            | grep -o '{[^{}]*"pkgname"[^{}]*}' \
            | grep -F "\"pkgname\": \"${pkg}\"" \
            | head -n1)"
        fname="$(printf '%s' "${row}" | grep -o '"filename": *"[^"]*"' | head -n1 | sed 's/.*"\([^"]*\)"$/\1/')"
        rep="$(printf '%s' "${row}" | grep -o '"repo": *"[^"]*"' | head -n1 | sed 's/.*"\([^"]*\)"$/\1/')"
        [[ -n "${fname}" && -n "${rep}" ]] || return 1
        url="https://geo.mirror.pkgbuild.com/${rep}/os/x86_64/${fname}"
        tmp="$(mktemp -d)"
        curl -fsSL --max-time 120 -o "${tmp}/p.pkg.tar.zst" "${url}" 2>/dev/null \
            || { rm -rf "${tmp}"; return 1; }
        mv "${tmp}/p.pkg.tar.zst" "${dest}/pkgs/${fname}"
        rm -rf "${tmp}"
    fi
    local extracted=0
    for f in "${dest}/pkgs/${pkg}-"*.pkg.tar.zst; do
        [[ -e "${f}" ]] || continue
        tar -xf "${f}" -C "${dest}" 2>/dev/null && extracted=1
    done
    [[ ${extracted} -eq 1 ]]
}

# Link user-space binaries fetched into syslibs/usr/bin onto PATH.
link_syslib_bins() {
    local dest="$HOME/.local/meshchatx-ci/syslibs"
    [[ -d "${dest}/usr/bin" ]] || return 0
    mkdir -p "${HOME}/.local/bin"
    local b
    for b in "${dest}/usr/bin"/*; do
        [[ -f "${b}" ]] || continue
        ln -sf "${b}" "${HOME}/.local/bin/$(basename "${b}")"
    done
    export PATH="${HOME}/.local/bin:${PATH}"
    if [[ -n "${GITHUB_PATH:-}" ]]; then
        echo "${HOME}/.local/bin" >> "$GITHUB_PATH"
    fi
}
