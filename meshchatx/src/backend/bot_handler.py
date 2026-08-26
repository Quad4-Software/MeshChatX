# SPDX-License-Identifier: 0BSD

import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

import RNS

from meshchatx.src.backend import bot_process as _bot_process  # noqa: F401
from meshchatx.src.backend.bot_lxmf_config import (
    describe_bot_lxmf_config,
    merge_bot_lxmf_overrides,
    normalize_bot_lxmf_overrides,
    resolve_effective_bot_lxmf_settings,
    validate_bot_lxmf_patch,
    write_bot_lxmf_config_sidecar,
)
from meshchatx.src.path_utils import atomic_write_text

logger = logging.getLogger("meshchatx.bots")

_LXMF_HASH_RE = re.compile(r"^[0-9a-f]{32}$")
_BOT_PROCESS_MODULE = "meshchatx.src.backend.bot_process"
# cx_Freeze / AppImage / macOS bundles set sys.executable to MeshChatX itself.
# meshchat.main() dispatches this flag to runpy.run_module before argparse.
_MESHCHATX_RUN_MODULE_FLAG = "--meshchatx-run-module"


class BotHandler:
    def __init__(
        self,
        identity_path,
        config_manager=None,
        default_reticulum_config_dir=None,
    ):
        """Manage LXMFy bot subprocesses for one identity.

        default_reticulum_config_dir should be the running app's own
        reticulum_config_dir so bots stay inside a custom --data-dir /
        --reticulum-config-dir root instead of leaking to the home
        directory. MESHCHAT_BOT_RETICULUM_CONFIG_DIR still overrides both,
        for callers that intentionally want bots on a separate RNS instance.
        """
        self.identity_path = os.path.abspath(identity_path)
        self.config_manager = config_manager
        fallback_reticulum_dir = default_reticulum_config_dir or "~/.reticulum"
        self.bot_reticulum_config_dir = os.path.abspath(
            os.path.expanduser(
                os.environ.get(
                    "MESHCHAT_BOT_RETICULUM_CONFIG_DIR",
                    fallback_reticulum_dir,
                ),
            ),
        )
        self.bots_dir = os.path.join(self.identity_path, "bots")
        os.makedirs(self.bots_dir, exist_ok=True)
        self.running_bots = {}
        self.state_file = os.path.join(self.bots_dir, "bots_state.json")
        self.bots_state: list[dict] = []
        self._state_unreadable = False
        self._load_state()
        self.runner_path = os.path.join(
            os.path.dirname(__file__),
            "bot_process.py",
        )

    @staticmethod
    def _is_frozen_executable():
        return bool(getattr(sys, "frozen", False))

    def _resolve_bot_launcher(self):
        """Return argv prefix for launching bot_process.

        Frozen desktop builds set sys.executable to MeshChatX itself. Passing
        a .py path as argv[1] starts another full app instance and hits the
        storage lock. Those builds re-enter via --meshchatx-run-module.
        """
        if self._is_frozen_executable():
            return [
                sys.executable,
                _MESHCHATX_RUN_MODULE_FLAG,
                _BOT_PROCESS_MODULE,
            ]
        return [sys.executable, self.runner_path]

    def _load_state(self):
        try:
            with open(self.state_file, encoding="utf-8") as f:
                loaded = json.load(f)
                if not isinstance(loaded, list):
                    self.bots_state = []
                    self._state_unreadable = True
                    return
                kept = []
                for entry in loaded:
                    if not isinstance(entry, dict):
                        continue
                    if "storage_dir" in entry:
                        entry["storage_dir"] = os.path.abspath(entry["storage_dir"])
                    if entry.get("bot_config_dir"):
                        entry["bot_config_dir"] = os.path.abspath(
                            os.path.expanduser(entry["bot_config_dir"]),
                        )
                    if entry.get("reticulum_config_dir"):
                        entry["reticulum_config_dir"] = os.path.abspath(
                            os.path.expanduser(entry["reticulum_config_dir"]),
                        )
                    if self._jailed_bot_dirs(entry) is None:
                        logger.warning(
                            "Dropping bot %s: storage path is outside the identity bots directory",
                            entry.get("id"),
                        )
                        continue
                    kept.append(entry)
                self.bots_state = kept
        except FileNotFoundError:
            self.bots_state = []
        except Exception:
            self.bots_state = []
            self._state_unreadable = True

    def _save_state(self):
        if self._state_unreadable:
            logger.error("Refusing to overwrite unreadable bots state file")
            return
        try:
            atomic_write_text(
                self.state_file,
                json.dumps(self.bots_state, indent=2),
            )
        except Exception as exc:
            logger.error("Failed to save bots state: %s", exc)

    def get_available_templates(self):
        return [
            {
                "id": "echo",
                "name": "Echo Bot",
                "description": "Repeats any message it receives.",
            },
            {
                "id": "note",
                "name": "Note Bot",
                "description": "Store and retrieve notes using JSON storage.",
            },
            {
                "id": "reminder",
                "name": "Reminder Bot",
                "description": "Set and receive reminders using SQLite storage.",
            },
        ]

    def restore_enabled_bots(self):
        for entry in list(self.bots_state):
            if entry.get("enabled"):
                try:
                    self.start_bot(
                        template_id=entry["template_id"],
                        name=entry["name"],
                        bot_id=entry["id"],
                        storage_dir=entry["storage_dir"],
                    )
                except Exception as exc:
                    logger.warning("Failed to restore bot %s: %s", entry.get("id"), exc)

    @staticmethod
    def _normalize_lxmf_hash_hex(value):
        if not value:
            return None
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, bytes):
            h = value.hex()
        else:
            h = str(value).strip().lower()
            h = h.replace(" ", "").replace("<", "").replace(">", "")
        if len(h) != 32 or not _LXMF_HASH_RE.match(h):
            return None
        return h

    @staticmethod
    def _read_lxmf_address_sidecar(storage_dir):
        if not storage_dir:
            return None
        path = os.path.join(storage_dir, "meshchatx_lxmf_address.txt")
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read().strip()
        except OSError:
            return None
        return BotHandler._normalize_lxmf_hash_hex(raw)

    @staticmethod
    def _read_bot_last_error(storage_dir):
        if not storage_dir:
            return None
        path = os.path.join(storage_dir, "meshchatx_bot_last_error.txt")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read().strip()
        except OSError:
            return None
        if not text:
            return None
        max_len = 1600
        if len(text) > max_len:
            return text[:max_len] + "\n..."
        return text

    @staticmethod
    def _subprocess_log_path(storage_dir):
        if not storage_dir:
            return None
        return os.path.join(storage_dir, "meshchatx_bot_subprocess.log")

    def read_subprocess_log(self, bot_id, max_bytes=524_288):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break
        if entry is None:
            raise ValueError(f"Unknown bot: {bot_id}")
        jailed = self._jailed_bot_dirs(entry)
        if jailed is None:
            raise ValueError("invalid bot storage directory")
        storage_dir, _bot_config_dir = jailed
        path = BotHandler._subprocess_log_path(storage_dir)
        if not path:
            return {"log": None, "truncated": False, "total_bytes": 0}
        if os.path.exists(path):
            jailed_path = self._jailed_file_under(
                storage_dir,
                "meshchatx_bot_subprocess.log",
            )
            if jailed_path is None:
                raise ValueError("invalid bot storage directory")
            path = jailed_path
        try:
            total = os.path.getsize(path)
        except OSError:
            return {"log": None, "truncated": False, "total_bytes": 0}
        if total == 0:
            return {"log": "", "truncated": False, "total_bytes": 0}
        truncated = total > max_bytes
        to_read = min(total, max_bytes)
        try:
            with open(path, "rb") as f:
                if truncated:
                    f.seek(total - to_read)
                raw = f.read()
        except OSError:
            return {"log": None, "truncated": False, "total_bytes": total}
        text = raw.decode("utf-8", errors="replace")
        if truncated and "\n" in text:
            _first, _sep, rest = text.partition("\n")
            text = rest or _first
        return {"log": text, "truncated": truncated, "total_bytes": total}

    def get_status(self):
        bots: list[dict] = []

        for entry in self.bots_state:
            bot_id = entry.get("id")
            template = entry.get("template_id") or entry.get("template")
            name = entry.get("name")
            if not name:
                name = f"{template.title()} Bot" if template else "Bot"
            pid = entry.get("pid")

            running = False
            if bot_id in self.running_bots:
                running = True
            elif pid:
                running = self._is_pid_alive(pid)

            address_pretty = None
            address_full = None

            # Try running instance first
            instance = self.running_bots.get(bot_id, {}).get("instance")
            if (
                instance
                and getattr(instance, "bot", None)
                and getattr(instance.bot, "local", None)
            ):
                with contextlib.suppress(Exception):
                    lh = instance.bot.local.hash
                    address_full = (
                        lh.hex() if isinstance(lh, (bytes, bytearray)) else None
                    )
                    if address_full:
                        address_full = self._normalize_lxmf_hash_hex(address_full)
                    if address_full:
                        address_pretty = RNS.prettyhexrep(bytes.fromhex(address_full))

            # Fallback to identity file on disk
            if address_full is None:
                identity = self._load_identity_for_bot(bot_id)
                if identity:
                    with contextlib.suppress(Exception):
                        destination = RNS.Destination(
                            identity,
                            RNS.Destination.OUT,
                            RNS.Destination.SINGLE,
                            "lxmf",
                            "delivery",
                        )
                        address_full = self._normalize_lxmf_hash_hex(destination.hash)
                        if address_full:
                            address_pretty = RNS.prettyhexrep(
                                bytes.fromhex(address_full),
                            )

            if address_full is None:
                address_full = self._read_lxmf_address_sidecar(entry.get("storage_dir"))
                if address_full:
                    with contextlib.suppress(Exception):
                        address_pretty = RNS.prettyhexrep(bytes.fromhex(address_full))

            storage_dir = entry.get("storage_dir")
            last_err = self._read_bot_last_error(storage_dir)
            lxmf_meta = describe_bot_lxmf_config(self.config_manager, entry)

            bots.append(
                {
                    "id": bot_id,
                    "template": template,
                    "template_id": template,
                    "name": name,
                    "address": address_pretty,
                    "lxmf_address": address_full,
                    "full_address": address_full,
                    "running": running,
                    "pid": pid,
                    "storage_dir": storage_dir,
                    "last_error": last_err,
                    "lxmf_config": lxmf_meta["lxmf_config"],
                    "effective_lxmf_config": lxmf_meta["effective_lxmf_config"],
                    "host_lxmf_propagation": lxmf_meta["host_lxmf_propagation"],
                },
            )

        return {
            "has_lxmfy": True,
            "detection_error": None,
            "running_bots": [b for b in bots if b["running"]],
            "bots": bots,
        }

    def start_bot(
        self,
        template_id,
        name=None,
        bot_id=None,
        storage_dir=None,
        lxmf_config=None,
    ):
        # Reuse existing entry or create new
        entry = None
        if bot_id:
            for e in self.bots_state:
                if e.get("id") == bot_id:
                    entry = e
                    break
        if entry is None:
            bot_id = bot_id or uuid.uuid4().hex
            bot_storage_dir = storage_dir or os.path.join(self.bots_dir, bot_id)
            bot_storage_dir = os.path.abspath(bot_storage_dir)
            jailed = self._jailed_bot_storage_dir(bot_storage_dir)
            if not jailed:
                msg = "Bot storage directory must be under the identity bots directory"
                raise ValueError(msg)
            bot_storage_dir = jailed
            entry = {
                "id": bot_id,
                "template_id": template_id,
                "name": name or f"{template_id.title()} Bot",
                "storage_dir": bot_storage_dir,
                "bot_config_dir": os.path.join(bot_storage_dir, "config"),
                "reticulum_config_dir": self.bot_reticulum_config_dir,
                "enabled": True,
                "pid": None,
            }
            self.bots_state.append(entry)
        else:
            jailed = self._jailed_bot_storage_dir(entry.get("storage_dir"))
            if not jailed:
                msg = "Bot storage directory must be under the identity bots directory"
                raise ValueError(msg)
            bot_storage_dir = jailed
            entry["storage_dir"] = bot_storage_dir
            entry["template_id"] = template_id
            entry["name"] = name or entry.get("name") or f"{template_id.title()} Bot"
            if not entry.get("bot_config_dir"):
                entry["bot_config_dir"] = os.path.join(bot_storage_dir, "config")
            if not entry.get("reticulum_config_dir"):
                entry["reticulum_config_dir"] = self.bot_reticulum_config_dir
            entry["enabled"] = True

        if lxmf_config is not None:
            validate_bot_lxmf_patch(lxmf_config)
            entry["lxmf_config"] = merge_bot_lxmf_overrides(
                entry.get("lxmf_config"),
                lxmf_config,
            )

        os.makedirs(bot_storage_dir, exist_ok=True)

        err_file = os.path.join(bot_storage_dir, "meshchatx_bot_last_error.txt")
        with contextlib.suppress(OSError):
            os.unlink(err_file)

        effective_lxmf = resolve_effective_bot_lxmf_settings(
            self.config_manager,
            entry,
        )
        lxmf_sidecar = write_bot_lxmf_config_sidecar(
            bot_storage_dir,
            effective_lxmf,
        )

        cmd = [
            *self._resolve_bot_launcher(),
            "--template",
            template_id,
            "--name",
            entry["name"],
            "--storage",
            bot_storage_dir,
            "--config-path",
            entry["bot_config_dir"],
            "--reticulum-config-dir",
            entry["reticulum_config_dir"],
            "--lxmf-config-file",
            lxmf_sidecar,
        ]

        subprocess_log = os.path.join(bot_storage_dir, "meshchatx_bot_subprocess.log")
        log_f = open(
            subprocess_log,
            "a",
            encoding="utf-8",
        )
        try:
            log_f.write(f"\n--- start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            log_f.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=bot_storage_dir,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except Exception:
            log_f.close()
            raise
        else:
            log_f.close()

        entry["pid"] = proc.pid
        self._save_state()

        self.running_bots[bot_id] = {
            "instance": None,
            "thread": None,
            "stop_event": None,
            "template": template_id,
            "pid": proc.pid,
            "proc": proc,
        }
        logger.info(f"Started bot {bot_id} (template: {template_id}) pid={proc.pid}")
        return bot_id

    def stop_bot(self, bot_id):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break
        if entry is None:
            return False

        pid = entry.get("pid")
        tracked = self.running_bots.get(bot_id) or {}
        proc = tracked.get("proc")
        if pid:
            try:
                if sys.platform.startswith("win"):
                    if proc is not None:
                        with contextlib.suppress(Exception):
                            proc.terminate()
                        with contextlib.suppress(Exception):
                            proc.wait(timeout=2)
                    if self._is_pid_alive(pid):
                        taskkill = shutil.which("taskkill") or "taskkill"
                        # Process may already have exited, so suppress "not found" noise.
                        subprocess.run(
                            [taskkill, "/PID", str(pid), "/T", "/F"],
                            check=False,
                            timeout=5,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                else:
                    try:
                        os.killpg(pid, 15)
                    except OSError:
                        os.kill(pid, 15)
                    # brief wait
                    time.sleep(0.5)
                    # optional force kill if still alive
                    try:
                        if self._is_pid_alive(pid):
                            try:
                                os.killpg(pid, 9)
                            except OSError:
                                os.kill(pid, 9)
                    except OSError:
                        pass
            except Exception as exc:
                logger.warning(
                    "Failed to terminate bot %s pid %s: %s",
                    bot_id,
                    pid,
                    exc,
                )
            self._reap_process(bot_id, pid)

        entry["pid"] = None
        entry["enabled"] = False
        self._save_state()
        if bot_id in self.running_bots:
            del self.running_bots[bot_id]
        logger.info("Stopped bot %s", bot_id)
        return True

    def restart_bot(self, bot_id):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break
        if entry is None:
            raise ValueError(f"Unknown bot: {bot_id}")
        self.stop_bot(bot_id)
        return self.start_bot(
            template_id=entry["template_id"],
            name=entry["name"],
            bot_id=bot_id,
            storage_dir=entry["storage_dir"],
        )

    def update_bot_lxmf_config(self, bot_id, lxmf_config):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break
        if entry is None:
            raise ValueError(f"Unknown bot: {bot_id}")
        if lxmf_config is None or not isinstance(lxmf_config, dict):
            raise ValueError("lxmf_config is required")
        validate_bot_lxmf_patch(lxmf_config)
        entry["lxmf_config"] = merge_bot_lxmf_overrides(
            entry.get("lxmf_config"),
            lxmf_config,
        )
        self._save_state()
        return normalize_bot_lxmf_overrides(entry["lxmf_config"])

    def update_bot_name(self, bot_id, name):
        raw = (name or "").strip()
        raw = re.sub(r"[\r\n]+", "", raw)
        if not raw:
            raise ValueError("name is required")
        if len(raw) > 256:
            raise ValueError("name too long")
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break
        if entry is None:
            raise ValueError(f"Unknown bot: {bot_id}")
        entry["name"] = raw
        self._save_state()
        sd = entry.get("storage_dir")
        if sd:
            try:
                cfg_dir = entry.get("bot_config_dir") or os.path.join(sd, "config")
                os.makedirs(cfg_dir, exist_ok=True)
                path = os.path.join(cfg_dir, "bot_display_name.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(raw)
            except OSError as exc:
                logger.warning("Failed to write bot display name file: %s", exc)
        return True

    def request_announce(self, bot_id):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break
        if entry is None:
            raise ValueError(f"Unknown bot: {bot_id}")
        pid = entry.get("pid")
        if not pid or not self._is_pid_alive(pid):
            raise RuntimeError("bot is not running")
        jailed = self._jailed_bot_dirs(entry)
        if jailed is None:
            raise RuntimeError("invalid bot storage directory")
        sd, _bot_config_dir = jailed
        req = os.path.join(sd, "meshchatx_request_announce")
        try:
            with open(req, "w", encoding="utf-8") as f:
                f.write("1")
        except OSError as exc:
            logger.warning("Failed to write announce request: %s", exc)
            raise RuntimeError("failed to write announce request") from exc
        return True

    def _jailed_bot_storage_dir(self, storage_dir):
        """Return realpath only when storage_dir is under this identity's bots dir."""
        if not storage_dir:
            return None
        bots_root = os.path.realpath(self.bots_dir)
        real = os.path.realpath(storage_dir)
        if real != bots_root and not real.startswith(bots_root + os.sep):
            return None
        return real

    def _jailed_bot_dirs(self, entry):
        """Return jailed (storage_dir, bot_config_dir) or None if either path escapes."""
        if not entry:
            return None
        storage_dir = self._jailed_bot_storage_dir(entry.get("storage_dir"))
        if not storage_dir:
            return None
        raw_cfg = entry.get("bot_config_dir")
        if raw_cfg:
            bot_config_dir = self._jailed_bot_storage_dir(raw_cfg)
            if not bot_config_dir:
                return None
        else:
            bot_config_dir = os.path.join(storage_dir, "config")
        return storage_dir, bot_config_dir

    def _jailed_file_under(self, root, *parts):
        if not root:
            return None
        candidate = os.path.join(root, *parts)
        if not os.path.exists(candidate):
            return None
        real = os.path.realpath(candidate)
        root_real = os.path.realpath(root)
        if real != root_real and not real.startswith(root_real + os.sep):
            return None
        return real

    def get_bot_identity_path(self, bot_id):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break

        if not entry:
            return None

        jailed = self._jailed_bot_dirs(entry)
        if jailed is None:
            return None
        storage_dir, bot_config_dir = jailed

        for path in (
            self._jailed_file_under(bot_config_dir, "identity"),
            self._jailed_file_under(bot_config_dir, "lxmf", "identity"),
        ):
            if path:
                return path

        reticulum_config_dir = entry.get("reticulum_config_dir")
        if reticulum_config_dir:
            allowed_shared = os.path.realpath(
                os.path.join(self.bot_reticulum_config_dir, "identity"),
            )
            candidate = os.path.realpath(
                os.path.join(os.path.expanduser(reticulum_config_dir), "identity"),
            )
            if candidate == allowed_shared and os.path.isfile(candidate):
                return candidate

        for path in (
            self._jailed_file_under(storage_dir, "config", "identity"),
            self._jailed_file_under(storage_dir, "identity"),
            self._jailed_file_under(storage_dir, "config", "lxmf", "identity"),
            self._jailed_file_under(storage_dir, "lxmf", "identity"),
        ):
            if path:
                return path

        return None

    def delete_bot(self, bot_id):
        # Stop it first
        self.stop_bot(bot_id)

        # Remove from state
        entry = None
        for i, e in enumerate(self.bots_state):
            if e.get("id") == bot_id:
                entry = e
                del self.bots_state[i]
                break

        if entry:
            # Delete storage dir only when jailed under bots/
            storage_dir = self._jailed_bot_storage_dir(entry.get("storage_dir"))
            if storage_dir and os.path.exists(storage_dir):
                try:
                    shutil.rmtree(storage_dir)
                except Exception as exc:
                    logger.warning(
                        "Failed to delete storage dir for bot %s: %s",
                        bot_id,
                        exc,
                    )

            self._save_state()
            logger.info("Deleted bot %s", bot_id)
            return True
        return False

    def _load_identity_for_bot(self, bot_id):
        identity_path = self.get_bot_identity_path(bot_id)
        if not identity_path:
            return None
        try:
            return RNS.Identity.from_file(identity_path)
        except Exception:
            return None

    @staticmethod
    def _is_pid_alive(pid):
        if not pid:
            return False
        if sys.platform.startswith("win"):
            return BotHandler._is_pid_alive_windows(pid)
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        # Reaped children are gone, but unreaped zombies still answer kill(0).
        if sys.platform.startswith("linux"):
            try:
                with open(f"/proc/{pid}/status", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("State:"):
                            # Z = zombie, X/x = dead
                            state = line.split(":", 1)[1].strip()
                            if state[:1] in ("Z", "X", "x"):
                                return False
                            break
            except OSError:
                return False
        return True

    @staticmethod
    def _is_pid_alive_windows(pid):
        """Return True only while the process is still running (not exited)."""
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            int(pid),
        )
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return int(code.value) == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)

    def _reap_process(self, bot_id, pid):
        tracked = self.running_bots.get(bot_id) or {}
        proc = tracked.get("proc")
        if proc is not None:
            with contextlib.suppress(Exception):
                proc.poll()
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)
            return
        if not pid:
            return
        # Best-effort reap when we still own the child (same parent).
        if hasattr(os, "waitpid"):
            with contextlib.suppress(ChildProcessError, OSError):
                os.waitpid(pid, os.WNOHANG)

    def stop_all(self):
        seen = set()
        for bot_id in list(self.running_bots.keys()):
            seen.add(bot_id)
            self.stop_bot(bot_id)
        for entry in list(self.bots_state):
            bot_id = entry.get("id")
            if not bot_id or bot_id in seen:
                continue
            pid = entry.get("pid")
            if pid and self._is_pid_alive(pid):
                self.stop_bot(bot_id)
