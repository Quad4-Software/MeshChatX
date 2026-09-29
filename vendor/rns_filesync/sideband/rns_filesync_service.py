# Sideband service plugin for RNS FileSync.
#
# Drop this file into Sideband's plugins directory and enable service plugins.
# Requires the rns-filesync package installed in the same Python environment
# as Sideband (pip, pipx, or pip-rns).
#
# Uses Sideband's identity and Reticulum instance. Sync directory, peers, and
# ACL come from ~/.rns_filesync/config (same as the CLI).

from __future__ import annotations

import os
import threading
import time

import RNS

from rns_filesync.cli import build_permissions
from rns_filesync.config import config_get, load_config, parse_csv_hashes
from rns_filesync.constants import ANNOUNCE_INTERVAL_DEFAULT
from rns_filesync.service import FileSyncService


class RnsFilesyncServicePlugin(SidebandServicePlugin):
    service_name = "rns_filesync"

    def __init__(self, sideband_core):
        super().__init__(sideband_core)
        self.service = None
        self._ready = threading.Event()
        self._boot_thread = None

    def start(self):
        RNS.log("RNS FileSync Sideband service plugin starting...", RNS.LOG_NOTICE)
        self._boot_thread = threading.Thread(
            target=self._boot_filesync,
            name="rns-filesync-sideband-boot",
            daemon=True,
        )
        self._boot_thread.start()
        super().start()

    def stop(self):
        if self.service is not None:
            try:
                self.service.stop()
            except Exception as exc:
                RNS.log(f"RNS FileSync stop error: {exc}", RNS.LOG_ERROR)
            self.service = None
        self._ready.clear()
        super().stop()

    def get_filesync(self):
        """Return the running FileSyncService, or None if not ready."""
        if not self._ready.is_set():
            return None
        return self.service

    def _wait_for_sideband(self, timeout: float = 120.0):
        sideband = self.get_sideband()
        deadline = time.time() + timeout
        while time.time() < deadline:
            identity = getattr(sideband, "identity", None)
            reticulum = getattr(sideband, "reticulum", None)
            if identity is not None and reticulum is not None:
                return identity, reticulum
            existing = None
            try:
                existing = RNS.Reticulum.get_instance()
            except Exception:
                existing = None
            if identity is not None and existing is not None:
                return identity, existing
            time.sleep(0.5)
        raise TimeoutError("Sideband identity/Reticulum not ready for FileSync")

    def _boot_filesync(self):
        try:
            identity, reticulum = self._wait_for_sideband()
            config_dir, config = load_config(None)

            directory = config_get(config, "filesync", "directory", None)
            if not directory:
                sideband = self.get_sideband()
                app_dir = getattr(sideband, "app_dir", None) or os.path.expanduser(
                    "~/.config/sideband",
                )
                directory = os.path.join(app_dir, "filesync")
            directory = os.path.realpath(os.path.expanduser(str(directory)))
            os.makedirs(directory, exist_ok=True)

            raw_interval = config_get(
                config,
                "filesync",
                "announce_interval",
                ANNOUNCE_INTERVAL_DEFAULT,
            )
            try:
                announce_interval = int(raw_interval)
            except (TypeError, ValueError):
                announce_interval = ANNOUNCE_INTERVAL_DEFAULT

            permissions = build_permissions(
                config=config,
                sync_directory=directory,
                allowed_path=None,
                allow_args=None,
                perms_shorthand="rwd",
            )

            self.service = FileSyncService(
                identity=identity,
                sync_directory=directory,
                reticulum=reticulum,
                permissions=permissions,
                own_reticulum=False,
            )
            dest = self.service.start(
                monitor=True,
                announce_interval=announce_interval,
            )
            self._ready.set()

            RNS.log(
                f"RNS FileSync ready dest={dest} dir={directory} config={config_dir}",
                RNS.LOG_NOTICE,
            )

            peers = parse_csv_hashes(config_get(config, "filesync", "peers", None))
            if peers:
                time.sleep(1.0)
                for peer in peers:
                    result = self.service.connect_peer(peer)
                    RNS.log(f"RNS FileSync connect {peer}: {result}", RNS.LOG_INFO)
        except Exception as exc:
            RNS.log(f"RNS FileSync Sideband plugin failed: {exc}", RNS.LOG_ERROR)
            RNS.trace_exception(exc)
            self.service = None
            self._ready.clear()


plugin_class = RnsFilesyncServicePlugin
