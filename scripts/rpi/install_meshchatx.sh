#!/usr/bin/env bash
set -euo pipefail

DEFAULT_WHEEL_URL="https://git.quad4.io/RNS-Things/MeshChatX/releases/download/v4.4.0/reticulum_meshchatx-4.4.0-py3-none-any.whl"

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
    local host="$1"
    local port="$2"
    python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((host, port))
except OSError:
    sys.exit(1)
finally:
    s.close()
sys.exit(0)
PY
}

detect_arch() {
    python3 - <<'PY'
import platform
print(platform.machine().strip().lower())
PY
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
        if python3 - "$scheme" "$probe_host" "$probe_port" <<'PY'
import json
import ssl
import sys
import urllib.request

scheme, host, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
url = f"{scheme}://{host}:{port}/api/v1/status"

ctx = ssl._create_unverified_context() if scheme == "https" else None
req = urllib.request.Request(url, method="GET")
try:
    with urllib.request.urlopen(req, timeout=2, context=ctx) as resp:
        if resp.status != 200:
            raise RuntimeError(f"unexpected status {resp.status}")
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "ok":
            raise RuntimeError("status payload is not ok")
except Exception:
    sys.exit(1)
sys.exit(0)
PY
        then
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

    local wheel_url
    wheel_url="$(prompt_default "Wheel URL" "$DEFAULT_WHEEL_URL")"

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

    if check_port_available "$bind_host" "$bind_port"; then
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
        run_as_user "pipx install --force '${wheel_url}'"
        run_as_user "pipx inject reticulum-meshchatx packaging >/dev/null 2>&1 || true"
        bin_path="${USER_HOME}/.local/bin/meshchatx"
    else
        note "Installing MeshChatX via venv + pip..."
        run_as_user "python3 -m venv '${venv_path}'"
        run_as_user "'${venv_path}/bin/python' -m pip install --upgrade pip"
        run_as_user "'${venv_path}/bin/python' -m pip install '${wheel_url}'"
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
