#!/usr/bin/env bash
set -euo pipefail

# Official defaults target Gitea at git.quad4.io. Override for forks or mirrors:
#   MESHCHATX_RELEASES_RSS  Release feed (default: .../MeshChatX/releases.rss)
#   MESHCHATX_REPO_BASE     Repo root for synthesized wheel URLs if RSS has no
#                           .whl link in descriptions (default: derived from RSS URL)
# Cosign: Sigstore attestation verify needs the real cosign binary; this script can
# download a checksum-verified release from GitHub to /tmp if none is on PATH.
#   MESHCHATX_COSIGN_VERSION   (default: 3.0.6)
#   MESHCHATX_COSIGN_PUB_URL   (default: raw cosign.pub from master in this repo)

RUN_USER="${SUDO_USER:-$USER}"
RUN_GROUP="$(id -gn "$RUN_USER")"
USER_HOME="$(eval echo "~${RUN_USER}")"

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
    C_RESET="$(tput sgr0)"
    C_BOLD="$(tput bold)"
    C_RED="$(tput setaf 1)"
    C_GREEN="$(tput setaf 2)"
    C_YELLOW="$(tput setaf 3)"
    C_BLUE="$(tput setaf 4)"
else
    C_RESET=""
    C_BOLD=""
    C_RED=""
    C_GREEN=""
    C_YELLOW=""
    C_BLUE=""
fi

note() {
    echo "${C_BLUE}${C_BOLD}==>${C_RESET} $*"
}

warn() {
    echo "${C_YELLOW}${C_BOLD}WARN:${C_RESET} $*"
}

err() {
    echo "${C_RED}${C_BOLD}ERROR:${C_RESET} $*" >&2
}

ok() {
    echo "${C_GREEN}${C_BOLD}OK:${C_RESET} $*"
}

run_as_user() {
    local cmd="$1"
    if [[ "$EUID" -eq 0 && "$RUN_USER" != "root" ]]; then
        sudo -u "$RUN_USER" -H bash -lc "$cmd"
    else
        bash -lc "$cmd"
    fi
}

prompt_default() {
    local prompt="$1"
    local default="$2"
    local value=""
    read -r -p "$prompt [$default]: " value
    if [[ -z "$value" ]]; then
        value="$default"
    fi
    echo "$value"
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local answer=""
    local hint="Y/n"
    if [[ "$default" == "n" ]]; then
        hint="y/N"
    fi

    while true; do
        read -r -p "$prompt ($hint): " answer
        if [[ -z "$answer" ]]; then
            answer="$default"
        fi
        case "${answer,,}" in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            *)
                echo "Please answer y or n."
                ;;
        esac
    done
}

repo_base_from_rss() {
    local u="$1"
    case "$u" in
        *"/releases.rss")
            echo "${u%/releases.rss}"
            ;;
        *"/releases.atom")
            echo "${u%/releases.atom}"
            ;;
        *)
            echo "${u%/*}"
            ;;
    esac
}

is_prerelease_tag() {
    local t="${1#v}"
    t="${t#V}"
    if [[ "$t" =~ (^|[-_.])(rc|RC|alpha|beta|pre|dev|a[0-9]+|b[0-9]+)([-_.[:digit:]]|$) ]]; then
        return 0
    fi
    return 1
}

absolutize_link() {
    local l="$1" o="$2"
    case "$l" in
        http://* | https://*) printf "%s" "$l" ;;
        //*)
            case "$o" in
                http://*)  printf "http:%s" "$l" ;;
                https://*) printf "https:%s" "$l" ;;
                *)         printf "https:%s" "$l" ;;
            esac
            ;;
        /*)
            local h="${o#*//}"
            h="${h%%/*}"
            case "$o" in
                http://*)  printf "http://%s%s" "$h" "$l" ;;
                https://*) printf "https://%s%s" "$h" "$l" ;;
                *)         printf "https://%s%s" "$h" "$l" ;;
            esac
            ;;
        *) printf "%s" "$l" ;;
    esac
}

tag_from_link() {
    local l="$1"
    if [[ "$l" =~ /releases/tag/([^/?#]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}

discover_release_wheels() {
    local rss raw repo_base st_tag st_url p_tag p_url
    if ! command -v curl >/dev/null 2>&1; then
        err "curl is required (RSS and downloads)."
        return 1
    fi
    MESHCHATX_RELEASES_RSS="${MESHCHATX_RELEASES_RSS:-https://git.quad4.io/RNS-Things/MeshChatX/releases.rss}"
    repo_base="${MESHCHATX_REPO_BASE:-}"
    rss="$MESHCHATX_RELEASES_RSS"
    [[ -n "$repo_base" ]] || repo_base="$(repo_base_from_rss "$rss")"
    if ! raw="$(
        curl -fsSL -m 90 -H "User-Agent: MeshChatX-rpi-installer/1 (+https://git.quad4.io/RNS-Things/MeshChatX)" \
            "$rss" 2>/dev/null
    )"; then
        return 1
    fi
    [[ -n "$raw" ]] || return 1
    st_tag=""; st_url=""; p_tag=""; p_url=""
    while IFS=$'\t' read -r alink itemblk || [[ -n "$alink" ]]; do
        [[ -z "$alink" && -z "$itemblk" ]] && continue
        local link t ver synth whl
        link="$(absolutize_link "$alink" "$rss")"
        t="$(tag_from_link "$link")"
        [[ -n "$t" ]] || continue
        whl="$(
            printf "%s" "$itemblk" | tr -d '\r' | awk '{
                s = $0
                while (match(s, /https?:\/\/[^[:space:]<&]+\.whl/)) {
                    w = substr(s, RSTART, RLENGTH)
                    if (w ~ /[Mm]eshchatx/) { print w; exit 0 }
                    s = substr(s, RSTART + 1)
                }
                s = $0
                while (match(s, /https?:\/\/[^[:space:]<&]+\.whl/)) {
                    print substr(s, RSTART, RLENGTH)
                    exit 0
                }
            }'
        )"
        ver="$t"
        if [[ "$ver" == v* ]]; then
            ver="${ver#v}"
        elif [[ "$ver" == V* ]]; then
            ver="${ver#V}"
        fi
        synth="${repo_base}/releases/download/${t}/reticulum_meshchatx-${ver}-py3-none-any.whl"
        if [[ -n "$whl" ]]; then
            link="$whl"
        else
            link="$synth"
        fi
        if is_prerelease_tag "$t"; then
            if [[ -z "$p_url" ]]; then
                p_tag="$t"
                p_url="$link"
            fi
        else
            if [[ -z "$st_url" ]]; then
                st_tag="$t"
                st_url="$link"
            fi
        fi
    done < <(
        printf '%s' "$raw" | tr -d '\r' | awk 'BEGIN{RS="<item>";} NR>1 {
    blk=$0
    gsub(/<atom:link/,"<link",blk);
    p=index(blk, "<link>");
    if (!p) next;
    s=substr(blk, p+6);
    q=index(s, "</link>");
    if (!q) next;
    l=substr(s, 1, q-1);
    gsub(/^[ \t\n]+/,"",l);
    gsub(/[ \t\n]+$/,"",l);
    print l "\t" blk
    }'
    )
    printf '%s\n' "$st_tag" "$st_url" "$p_tag" "$p_url"
}

prompt_wheel_source() {
    local stable_tag="$1"
    local stable_url="$2"
    local pre_tag="$3"
    local pre_url="$4"

    local choice="" default_choice="1"
    echo
    note "Pick the MeshChatX wheel (from Gitea release feed)."
    if [[ -n "$stable_tag" && -n "$stable_url" ]]; then
        echo "  1) stable (${stable_tag})"
    else
        echo "  1) stable (not available from feed)"
        default_choice="3"
    fi
    if [[ -n "$pre_tag" && -n "$pre_url" ]]; then
        echo "  2) pre-release (${pre_tag})"
    else
        echo "  2) pre-release (not available from feed)"
    fi
    echo "  3) custom wheel URL"
    if [[ -z "$stable_url" && -z "$pre_url" ]]; then
        default_choice="3"
    elif [[ -z "$stable_url" && -n "$pre_url" ]]; then
        default_choice="2"
    fi

    while true; do
        read -r -p "Selection [1/2/3] (default ${default_choice}): " choice
        if [[ -z "$choice" ]]; then
            choice="$default_choice"
        fi
        case "$choice" in
            1)
                if [[ -n "$stable_url" ]]; then
                    echo "$stable_url"
                    return 0
                fi
                echo "Stable wheel is not available; choose 2 or 3." >&2
                ;;
            2)
                if [[ -n "$pre_url" ]]; then
                    echo "$pre_url"
                    return 0
                fi
                echo "Pre-release wheel is not available; choose 1 or 3." >&2
                ;;
            3)
                local custom_u=""
                custom_u="$(prompt_default "Wheel URL" "")"
                if [[ -z "$custom_u" ]]; then
                    echo "URL cannot be empty." >&2
                else
                    echo "$custom_u"
                    return 0
                fi
                ;;
            *)
                echo "Please enter 1, 2, or 3." >&2
                ;;
        esac
    done
}

pick_package_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "apt"
        return
    fi
    if command -v dnf >/dev/null 2>&1; then
        echo "dnf"
        return
    fi
    if command -v pacman >/dev/null 2>&1; then
        echo "pacman"
        return
    fi
    echo "none"
}

install_package_if_possible() {
    local package="$1"
    local mgr
    mgr="$(pick_package_manager)"
    case "$mgr" in
        apt)
            if [[ "$EUID" -eq 0 ]]; then
                apt-get update && apt-get install -y "$package"
            else
                sudo apt-get update && sudo apt-get install -y "$package"
            fi
            ;;
        dnf)
            if [[ "$EUID" -eq 0 ]]; then
                dnf install -y "$package"
            else
                sudo dnf install -y "$package"
            fi
            ;;
        pacman)
            if [[ "$EUID" -eq 0 ]]; then
                pacman -Sy --noconfirm "$package"
            else
                sudo pacman -Sy --noconfirm "$package"
            fi
            ;;
        none)
            warn "No supported package manager found (apt/dnf/pacman). Skipping install for $package."
            ;;
    esac
}

check_port_available() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        if ss -tlnH 2>/dev/null | grep -qE ":${port}( |$)"; then
            return 1
        fi
        return 0
    fi
    if command -v netstat >/dev/null 2>&1; then
        if netstat -tln 2>/dev/null | grep -qE ":${port}( |$)"; then
            return 1
        fi
        return 0
    fi
    warn "ss/netstat not found; port availability not checked."
    return 0
}

detect_arch() {
    uname -m | tr '[:upper:]' '[:lower:]'
}

is_supported_rpi_arch() {
    local arch="$1"
    case "$arch" in
        armv6l|armv7l|aarch64|arm64)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

write_system_service() {
    local exec_cmd="$1"
    local workdir="$2"
    local path_value="$3"
    local svc="/etc/systemd/system/meshchatx.service"

    if [[ "$EUID" -eq 0 ]]; then
        SUDO=""
    else
        SUDO="sudo"
    fi

    $SUDO tee "$svc" >/dev/null <<EOF
[Unit]
Description=MeshChatX Headless (system service)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${workdir}
Environment="PATH=${path_value}"
ExecStart=${exec_cmd}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
}

write_user_service() {
    local exec_cmd="$1"
    local workdir="$2"
    local path_value="$3"
    local svc_path="${USER_HOME}/.config/systemd/user/meshchatx.service"

    run_as_user "mkdir -p '${USER_HOME}/.config/systemd/user'"
    run_as_user "cat > '${svc_path}' <<'EOF'
[Unit]
Description=MeshChatX Headless (user service)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=${workdir}
Environment=\"PATH=${path_value}\"
ExecStart=${exec_cmd}
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF"
}

api_status_is_ok() {
    local scheme="$1"
    local h="$2"
    local p="$3"
    local url="${scheme}://${h}:${p}/api/v1/status"
    if command -v curl >/dev/null 2>&1; then
        if [[ "$scheme" == "https" ]]; then
            curl -fsS -k -m 2 "$url" 2>/dev/null | grep -qE '"status"[[:space:]]*:[[:space:]]*"ok"'
        else
            curl -fsS -m 2 "$url" 2>/dev/null | grep -qE '"status"[[:space:]]*:[[:space:]]*"ok"'
        fi
    elif command -v wget >/dev/null 2>&1; then
        if [[ "$scheme" == "https" ]]; then
            wget -qO- -T 2 --no-check-certificate "$url" 2>/dev/null | grep -qE '"status"[[:space:]]*:[[:space:]]*"ok"'
        else
            wget -qO- -T 2 "$url" 2>/dev/null | grep -qE '"status"[[:space:]]*:[[:space:]]*"ok"'
        fi
    else
        return 1
    fi
}

ensure_cosign_binary() {
    local u ver bin_name expect act tmpd sumf base
    u="$(uname -m)"
    case "$u" in
        x86_64)   bin_name="cosign-linux-amd64" ;;
        aarch64)  bin_name="cosign-linux-arm64" ;;
        arm64)    bin_name="cosign-linux-arm64" ;;
        armv7l | armv6l) bin_name="cosign-linux-arm" ;;
        *)
            err "No bootstrap cosign build for uname: $u (install cosign, or skip attestation verify)."
            return 1
            ;;
    esac
    ver="${MESHCHATX_COSIGN_VERSION:-3.0.6}"
    tmpd="${TMPDIR:-/tmp}/meshchatx-cosign-${$}"
    mkdir -p "$tmpd" || return 1
    sumf="${tmpd}/cosign_checksums.txt"
    base="https://github.com/sigstore/cosign/releases/download/v${ver}"
    if ! curl -fsSL -m 120 "$base/cosign_checksums.txt" -o "$sumf" \
        || ! curl -fsSL -m 120 "$base/${bin_name}" -o "${tmpd}/cosign"; then
        rm -rf "$tmpd"
        err "Could not download cosign ${ver} for verification."
        return 1
    fi
    expect="$(awk -v b="$bin_name" 'index($0, b) {print $1; exit}' "$sumf" 2>/dev/null || true)"
    act="$(sha256sum "${tmpd}/cosign" | awk '{print $1}')"
    if [[ -z "$expect" || "$expect" != "$act" ]]; then
        rm -rf "$tmpd"
        err "cosign binary SHA256 mismatch (expected from checksums: ${expect:-missing})."
        return 1
    fi
    chmod 755 "${tmpd}/cosign"
    echo "${tmpd}/cosign"
}

try_verify_and_localize_wheel() {
    MESHCHATX_WHEEL_FILE=""
    local src_url="${1:-}"
    local bundle_url="${src_url}.cosign.bundle"
    local code cbin kf wf bf
    MESHCHATX_COSIGN_PUB_URL="${MESHCHATX_COSIGN_PUB_URL:-https://git.quad4.io/RNS-Things/MeshChatX/raw/branch/master/cosign.pub}"
    if ! code="$(curl -fsS -o /dev/null -w '%{http_code}' -I -L -m 30 "$bundle_url" 2>/dev/null)"; then
        code="000"
    fi
    [[ "$code" == "200" ]] || return 1
    if ! prompt_yes_no "A cosign attestation exists for this wheel. Verify with cosign (uses PATH binary, or one-time download to /tmp, not a system package)?" "y"; then
        return 1
    fi
    wf="$(mktemp "${TMPDIR:-/tmp}/meshchatx.XXXXXX.whl")" || return 1
    bf="$(mktemp "${TMPDIR:-/tmp}/meshchatx.XXXXXX.cosign.bundle")" || {
        rm -f "$wf"
        return 1
    }
    kf="$(mktemp "${TMPDIR:-/tmp}/meshchatx.XXXXXX.pub")" || {
        rm -f "$wf" "$bf"
        return 1
    }
    if ! curl -fsSL -m 600 "$src_url" -o "$wf" || ! curl -fsSL -m 120 "$bundle_url" -o "$bf" || ! curl -fsSL -m 60 "$MESHCHATX_COSIGN_PUB_URL" -o "$kf"; then
        err "Failed to download wheel, bundle, or cosign.pub."
        rm -f "$wf" "$bf" "$kf"
        return 1
    fi
    if command -v cosign >/dev/null 2>&1; then
        cbin="$(command -v cosign)"
    elif ! cbin="$(ensure_cosign_binary)"; then
        err "Set cosign on PATH, or use a build arch supported by the Sigstore binary."
        rm -f "$wf" "$bf" "$kf"
        return 1
    fi
    if ! "$cbin" verify-blob-attestation --key "$kf" --bundle "$bf" --type slsaprovenance1 "$wf"; then
        err "cosign attestation verification failed for the downloaded wheel."
        rm -f "$wf" "$bf" "$kf"
        exit 1
    fi
    rm -f "$bf" "$kf"
    MESHCHATX_WHEEL_FILE="$wf"
    ok "cosign attestation OK (SLSA provenance v1). Installing verified wheel from ${wf}."
    return 0
}

handle_service_start_failure() {
    local mode="$1"
    local reason="$2"

    err "$reason"
    warn "Service startup failed. Recent logs:"
    if [[ "$mode" == "system" ]]; then
        sudo journalctl -u meshchatx.service -n 200 --no-pager || true
        sudo systemctl stop meshchatx.service || true
        sudo systemctl reset-failed meshchatx.service || true
    else
        run_as_user "journalctl --user -u meshchatx.service -n 200 --no-pager" || true
        run_as_user "systemctl --user stop meshchatx.service || true"
        run_as_user "systemctl --user reset-failed meshchatx.service || true"
    fi
    err "Service was stopped/reset. Fix config and run installer again."
    exit 1
}

verify_service_started() {
    local mode="$1"
    local probe_host="$2"
    local probe_port="$3"
    local https_enabled="$4"
    local tries=40
    local log_cmd=""
    local stop_cmd=""
    local scheme="https"
    if [[ "$https_enabled" == "no" ]]; then
        scheme="http"
    fi

    if [[ "$mode" == "system" ]]; then
        log_cmd="sudo journalctl -u meshchatx.service -n 200 --no-pager"
        stop_cmd="sudo systemctl stop meshchatx.service; sudo systemctl reset-failed meshchatx.service"
    else
        log_cmd="journalctl --user -u meshchatx.service -n 200 --no-pager"
        stop_cmd="systemctl --user stop meshchatx.service || true; systemctl --user reset-failed meshchatx.service || true"
    fi

    note "Verifying service startup via ${scheme}://${probe_host}:${probe_port}/api/v1/status ..."
    for _ in $(seq 1 "$tries"); do
        if api_status_is_ok "$scheme" "$probe_host" "$probe_port"; then
            ok "Service started successfully (status endpoint is healthy)."
            return 0
        fi
        sleep 1
    done

    err "Service did not pass status endpoint health check."
    warn "Recent logs:"
    if [[ "$mode" == "system" ]]; then
        sudo journalctl -u meshchatx.service -n 200 --no-pager || true
        eval "$stop_cmd"
    else
        run_as_user "$log_cmd" || true
        run_as_user "$stop_cmd"
    fi
    err "Service was stopped to prevent restart loops."
    return 1
}

main() {
    note "MeshChatX Raspberry Pi Interactive Installer"
    echo "Detected user: ${RUN_USER} (group: ${RUN_GROUP})"
    local arch
    arch="$(detect_arch)"
    echo "Detected architecture: ${arch}"
    if is_supported_rpi_arch "$arch"; then
        ok "Detected Raspberry Pi ARM architecture (${arch})."
    else
        warn "Detected non-RPi arch (${arch}). Script can still run, but this guide targets Raspberry Pi ARM."
    fi
    note "The wheel is py3-none-any, so it is architecture-independent (32-bit and 64-bit ARM are supported)."
    echo

    if prompt_yes_no "Do you want to install espeak-ng?" "y"; then
        note "Installing espeak-ng (best effort)..."
        if ! install_package_if_possible "espeak-ng"; then
            warn "Could not install espeak-ng automatically; continuing."
        fi
    else
        note "Skipping espeak-ng installation."
    fi

    local method_choice=""
    while [[ "$method_choice" != "1" && "$method_choice" != "2" ]]; do
        echo
        echo "Choose installation method:"
        echo "  1) pipx (recommended)"
        echo "  2) venv + pip"
        read -r -p "Selection [1/2]: " method_choice
        if [[ -z "$method_choice" ]]; then
            method_choice="1"
        fi
    done

    local wheel_url=""
    local -a rel_lines=()
    note "Fetching release list from Gitea (RSS)..."
    if mapfile -t rel_lines < <(discover_release_wheels 2>/dev/null) && [[ ${#rel_lines[@]} -ge 4 ]]; then
        wheel_url="$(prompt_wheel_source "${rel_lines[0]:-}" "${rel_lines[1]:-}" "${rel_lines[2]:-}" "${rel_lines[3]:-}")"
    else
        warn "Could not use the release feed (set MESHCHATX_RELEASES_RSS or check network)."
        wheel_url="$(prompt_default "Wheel URL" "")"
        if [[ -z "$wheel_url" ]]; then
            err "Aborted: need a wheel URL."
            exit 1
        fi
    fi
    ok "Selected wheel: ${wheel_url}"
    local wheel_install_target="$wheel_url"
    MESHCHATX_WHEEL_FILE=""
    if try_verify_and_localize_wheel "$wheel_url"; then
        wheel_install_target="${MESHCHATX_WHEEL_FILE}"
    fi

    local install_root
    install_root="$(prompt_default "Install root directory" "${USER_HOME}/meshchatx")"
    local storage_dir
    storage_dir="$(prompt_default "Storage directory" "${install_root}/storage")"
    local rns_dir
    rns_dir="$(prompt_default "Reticulum config directory" "${USER_HOME}/.reticulum")"
    local bind_host
    bind_host="$(prompt_default "Bind IP/host" "0.0.0.0")"
    local bind_port
    bind_port="$(prompt_default "Bind port" "8000")"

    if check_port_available "$bind_port"; then
        ok "Port ${bind_port} is available on ${bind_host}."
    else
        warn "Port ${bind_port} appears to be in use on ${bind_host}."
        if ! prompt_yes_no "Continue anyway?" "n"; then
            err "Aborted."
            exit 1
        fi
    fi

    local https_enabled="yes"
    if ! prompt_yes_no "Enable HTTPS?" "y"; then
        https_enabled="no"
    fi

    local service_mode="none"
    if prompt_yes_no "Do you want to configure a systemd service?" "y"; then
        service_mode=""
        while [[ "$service_mode" != "system" && "$service_mode" != "user" ]]; do
            service_mode="$(prompt_default "Service mode (system/user)" "system")"
        done
    fi

    local no_https_flag=""
    if [[ "$https_enabled" == "no" ]]; then
        no_https_flag=" --no-https"
    fi

    local probe_host="$bind_host"
    if [[ "$bind_host" == "0.0.0.0" ]]; then
        probe_host="127.0.0.1"
    elif [[ "$bind_host" == "::" ]]; then
        probe_host="::1"
    fi

    note "Preparing directories..."
    if [[ "$EUID" -eq 0 ]]; then
        install -d -m 755 -o "$RUN_USER" -g "$RUN_GROUP" "$install_root" "$storage_dir" "$rns_dir"
    else
        mkdir -p "$install_root" "$storage_dir" "$rns_dir"
        if command -v sudo >/dev/null 2>&1; then
            sudo install -d -m 755 -o "$RUN_USER" -g "$RUN_GROUP" "$install_root" "$storage_dir" "$rns_dir" >/dev/null 2>&1 || true
        fi
    fi

    local bin_path=""
    local venv_path="${install_root}/.venv"

    if [[ "$method_choice" == "1" ]]; then
        if ! command -v pipx >/dev/null 2>&1; then
            err "pipx not found. Install pipx first or choose venv method."
            exit 1
        fi
        note "Installing MeshChatX via pipx..."
        run_as_user "pipx ensurepath >/dev/null 2>&1 || true"
        run_as_user "pipx install --force '${wheel_install_target}'"
        run_as_user "pipx inject reticulum-meshchatx packaging >/dev/null 2>&1 || true"
        bin_path="${USER_HOME}/.local/bin/meshchatx"
    else
        note "Installing MeshChatX via venv + pip..."
        run_as_user "python3 -m venv '${venv_path}'"
        run_as_user "'${venv_path}/bin/python' -m pip install --upgrade pip"
        run_as_user "'${venv_path}/bin/python' -m pip install '${wheel_install_target}'"
        run_as_user "'${venv_path}/bin/python' -m pip install packaging"
        bin_path="${venv_path}/bin/meshchatx"
    fi

    if [[ ! -x "$bin_path" ]]; then
        err "meshchatx binary not found at: $bin_path"
        exit 1
    fi

    local exec_cmd="${bin_path} --headless --host ${bind_host} --port ${bind_port} --storage-dir ${storage_dir} --reticulum-config-dir ${rns_dir}${no_https_flag}"
    local path_env="${venv_path}/bin:${USER_HOME}/.local/bin:/usr/bin:/bin"

    if [[ "$service_mode" == "none" ]]; then
        ok "Install complete."
        echo
        echo "Run command:"
        echo "  ${exec_cmd}"
        exit 0
    fi

    if [[ "$service_mode" == "system" ]]; then
        note "Creating system service..."
        write_system_service "$exec_cmd" "$install_root" "$path_env"
        if [[ "$EUID" -eq 0 ]]; then
            if ! systemctl daemon-reload; then
                handle_service_start_failure "system" "systemctl daemon-reload failed."
            fi
            if ! systemctl enable --now meshchatx.service; then
                handle_service_start_failure "system" "systemctl enable/start failed."
            fi
        else
            if ! sudo systemctl daemon-reload; then
                handle_service_start_failure "system" "sudo systemctl daemon-reload failed."
            fi
            if ! sudo systemctl enable --now meshchatx.service; then
                handle_service_start_failure "system" "sudo systemctl enable/start failed."
            fi
        fi
        if ! verify_service_started "system" "$probe_host" "$bind_port" "$https_enabled"; then
            exit 1
        fi
        ok "System service is enabled and running."
    else
        if [[ "$service_mode" == "user" ]]; then
            note "Creating user service..."
            write_user_service "$exec_cmd" "$install_root" "$path_env"
            if ! run_as_user "systemctl --user daemon-reload"; then
                handle_service_start_failure "user" "systemctl --user daemon-reload failed."
            fi
            if ! run_as_user "systemctl --user enable --now meshchatx.service"; then
                handle_service_start_failure "user" "systemctl --user enable/start failed."
            fi
            if ! verify_service_started "user" "$probe_host" "$bind_port" "$https_enabled"; then
                exit 1
            fi
            ok "User service is enabled and running."
        fi
    fi

    echo
    echo "Web UI:"
    echo "  https://${bind_host}:${bind_port}"
    if [[ "$https_enabled" == "no" ]]; then
        echo "  (HTTP mode enabled)"
    fi
}

main "$@"
