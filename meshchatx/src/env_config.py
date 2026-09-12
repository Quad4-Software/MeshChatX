# SPDX-License-Identifier: 0BSD

"""Startup snapshot of MeshChatX environment variables.

One catalog of honoured MESHCHAT_* variables, parsed once through
env_utils so CLI flags and feature code share identical parsing rules.
Load at startup with MeshchatEnv.load(); do not snapshot at import
time so tests can still monkeypatch os.environ before constructing it.
"""

from __future__ import annotations

# pyright: strict
from dataclasses import dataclass

from meshchatx.src.env_utils import env_bool, env_int, env_str


@dataclass(frozen=True)
class MeshchatEnv:
    host: str = "127.0.0.1"
    port: int = 8000
    headless: bool = False
    data_dir: str | None = None
    storage_dir: str | None = None
    reticulum_config_dir: str | None = None
    public_dir: str | None = None
    log_dir: str | None = None
    auth: bool = False
    auth_bypass: bool = False
    auth_page_hint: bool = False
    no_https: bool = False
    ssl_cert: str | None = None
    ssl_key: str | None = None
    identity_file: str | None = None
    identity_base64: str | None = None
    identity_base32: str | None = None
    auto_recover: bool = False
    emergency: bool = False
    reset_password: bool = False
    restore_snapshot: str | None = None
    disable_plugins: bool = False
    self_check: bool = False
    memory_diag: bool = False
    disable_csrf: bool = False
    skip_storage_lock: bool = False
    skip_legacy_migration_ui: bool = False
    no_crash_recovery: bool = False
    pre_migrate_backup_keep: str | None = None
    landlock: str | None = None
    seccomp: str | None = None
    appcontainer_launcher: str | None = None
    rns_log_level: str | None = None
    rns_log_dest: str | None = None
    demo_mode: bool = False
    demo_auth_password: str | None = None
    force_web_audio: bool = False
    experimental_webtransport: bool = False
    repository_extra_pip: str | None = None
    gitea_base_url: str | None = None
    trusted_proxies: str | None = None
    bot_reticulum_config_dir: str | None = None
    self_check_probe_path: str | None = None
    debugpy: bool = False
    debugpy_port: int = 5678
    debugpy_wait: bool = False
    vue_devtools: bool = True

    @classmethod
    def load(cls) -> MeshchatEnv:
        """Read the process environment once, at startup."""
        return cls(
            host=env_str("MESHCHAT_HOST", "127.0.0.1") or "127.0.0.1",
            port=env_int("MESHCHAT_PORT", 8000) or 8000,
            headless=env_bool("MESHCHAT_HEADLESS"),
            data_dir=env_str("MESHCHAT_DATA_DIR"),
            storage_dir=env_str("MESHCHAT_STORAGE_DIR"),
            reticulum_config_dir=env_str("MESHCHAT_RETICULUM_CONFIG_DIR"),
            public_dir=env_str("MESHCHAT_PUBLIC_DIR"),
            log_dir=env_str("MESHCHAT_LOG_DIR"),
            auth=env_bool("MESHCHAT_AUTH"),
            auth_bypass=env_bool("MESHCHAT_AUTH_BYPASS"),
            auth_page_hint=env_bool("MESHCHAT_AUTH_PAGE_HINT"),
            no_https=env_bool("MESHCHAT_NO_HTTPS"),
            ssl_cert=env_str("MESHCHAT_SSL_CERT"),
            ssl_key=env_str("MESHCHAT_SSL_KEY"),
            identity_file=env_str("MESHCHAT_IDENTITY_FILE"),
            identity_base64=env_str("MESHCHAT_IDENTITY_BASE64"),
            identity_base32=env_str("MESHCHAT_IDENTITY_BASE32"),
            auto_recover=env_bool("MESHCHAT_AUTO_RECOVER"),
            emergency=env_bool("MESHCHAT_EMERGENCY"),
            reset_password=env_bool("MESHCHAT_RESET_PASSWORD"),
            restore_snapshot=env_str("MESHCHAT_RESTORE_SNAPSHOT"),
            disable_plugins=env_bool("MESHCHAT_DISABLE_PLUGINS"),
            self_check=env_bool("MESHCHAT_SELF_CHECK"),
            memory_diag=env_bool("MESHCHAT_MEMORY_DIAG"),
            disable_csrf=env_bool("MESHCHAT_DISABLE_CSRF"),
            skip_storage_lock=env_bool("MESHCHAT_SKIP_STORAGE_LOCK"),
            skip_legacy_migration_ui=env_bool("MESHCHAT_SKIP_LEGACY_MIGRATION_UI"),
            no_crash_recovery=env_bool("MESHCHAT_NO_CRASH_RECOVERY"),
            pre_migrate_backup_keep=env_str("MESHCHAT_PRE_MIGRATE_BACKUP_KEEP"),
            landlock=env_str("MESHCHAT_LANDLOCK"),
            seccomp=env_str("MESHCHAT_SECCOMP"),
            appcontainer_launcher=env_str("MESHCHAT_APPCONTAINER_LAUNCHER"),
            rns_log_level=env_str("MESHCHAT_RNS_LOG_LEVEL"),
            rns_log_dest=env_str("MESHCHAT_RNS_LOG_DEST"),
            demo_mode=env_bool("MESHCHAT_DEMO_MODE"),
            demo_auth_password=env_str("MESHCHAT_DEMO_AUTH_PASSWORD"),
            force_web_audio=env_bool("MESHCHAT_FORCE_WEB_AUDIO"),
            experimental_webtransport=env_bool("MESHCHAT_EXPERIMENTAL_WEBTRANSPORT"),
            repository_extra_pip=env_str("MESHCHAT_REPOSITORY_EXTRA_PIP"),
            gitea_base_url=env_str("MESHCHAT_GITEA_BASE_URL"),
            trusted_proxies=env_str("MESHCHAT_TRUSTED_PROXIES"),
            bot_reticulum_config_dir=env_str("MESHCHAT_BOT_RETICULUM_CONFIG_DIR"),
            self_check_probe_path=env_str("MESHCHATX_SELF_CHECK_PROBE_PATH"),
            debugpy=env_bool("MESHCHAT_DEBUGPY"),
            debugpy_port=env_int("MESHCHAT_DEBUGPY_PORT", 5678) or 5678,
            debugpy_wait=env_bool("MESHCHAT_DEBUGPY_WAIT"),
            vue_devtools=env_bool("MESHCHAT_VUE_DEVTOOLS", True),
        )
