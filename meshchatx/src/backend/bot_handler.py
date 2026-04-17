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

logger = logging.getLogger("meshchatx.bots")

_LXMF_HASH_RE = re.compile(r"^[0-9a-f]{32}$")


class BotHandler:
    def __init__(self, identity_path, config_manager=None):
        self.identity_path = os.path.abspath(identity_path)
        self.config_manager = config_manager
        self.bot_reticulum_config_dir = os.path.abspath(
            os.path.expanduser(
                os.environ.get("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", "~/.reticulum"),
            ),
        )
        self.bots_dir = os.path.join(self.identity_path, "bots")
        os.makedirs(self.bots_dir, exist_ok=True)
        self.running_bots = {}
        self.state_file = os.path.join(self.bots_dir, "bots_state.json")
        self.bots_state: list[dict] = []
        self._load_state()
        self.runner_path = os.path.join(
            os.path.dirname(__file__),
            "bot_process.py",
        )

    def _load_state(self):
        try:
            with open(self.state_file, encoding="utf-8") as f:
                self.bots_state = json.load(f)
                # Ensure all storage paths are absolute
                for entry in self.bots_state:
                    if "storage_dir" in entry:
                        entry["storage_dir"] = os.path.abspath(entry["storage_dir"])
                    if "bot_config_dir" in entry and entry["bot_config_dir"]:
                        entry["bot_config_dir"] = os.path.abspath(
                            os.path.expanduser(entry["bot_config_dir"]),
                        )
                    if (
                        "reticulum_config_dir" in entry
                        and entry["reticulum_config_dir"]
                    ):
                        entry["reticulum_config_dir"] = os.path.abspath(
                            os.path.expanduser(entry["reticulum_config_dir"]),
                        )
        except FileNotFoundError:
            self.bots_state = []
        except Exception:
            self.bots_state = []

    def _save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.bots_state, f, indent=2)
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
                    address_full = lh.hex() if isinstance(lh, (bytes, bytearray)) else None
                    if address_full:
                        address_full = self._normalize_lxmf_hash_hex(address_full)
                    if address_full:
                        address_pretty = RNS.prettyhexrep(bytes.fromhex(address_full))

            # Fallback to identity file on disk
            if address_full is None:
                identity = self._load_identity_for_bot(bot_id)
                if identity:
                    with contextlib.suppress(Exception):
                        destination = RNS.Destination(identity, "lxmf", "delivery")
                        address_full = self._normalize_lxmf_hash_hex(destination.hash)
                        if address_full:
                            address_pretty = RNS.prettyhexrep(bytes.fromhex(address_full))

            if address_full is None:
                address_full = self._read_lxmf_address_sidecar(entry.get("storage_dir"))
                if address_full:
                    with contextlib.suppress(Exception):
                        address_pretty = RNS.prettyhexrep(bytes.fromhex(address_full))

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
                    "storage_dir": entry.get("storage_dir"),
                },
            )

        return {
            "has_lxmfy": True,
            "detection_error": None,
            "running_bots": [b for b in bots if b["running"]],
            "bots": bots,
        }

    def start_bot(self, template_id, name=None, bot_id=None, storage_dir=None):
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
            bot_storage_dir = entry["storage_dir"]
            entry["template_id"] = template_id
            entry["name"] = name or entry.get("name") or f"{template_id.title()} Bot"
            if not entry.get("bot_config_dir"):
                entry["bot_config_dir"] = os.path.join(bot_storage_dir, "config")
            if not entry.get("reticulum_config_dir"):
                entry["reticulum_config_dir"] = self.bot_reticulum_config_dir
            entry["enabled"] = True

        os.makedirs(bot_storage_dir, exist_ok=True)

        cmd = [
            sys.executable,
            self.runner_path,
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
        ]

        proc = subprocess.Popen(cmd, cwd=bot_storage_dir)  # noqa: S603
        entry["pid"] = proc.pid
        self._save_state()

        self.running_bots[bot_id] = {
            "instance": None,
            "thread": None,
            "stop_event": None,
            "template": template_id,
            "pid": proc.pid,
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
        if pid:
            try:
                if sys.platform.startswith("win"):
                    # Use absolute path if possible to avoid S607
                    taskkill = shutil.which("taskkill") or "taskkill"
                    subprocess.run(  # noqa: S603
                        [taskkill, "/PID", str(pid), "/T", "/F"],
                        check=False,
                        timeout=5,
                    )
                else:
                    os.kill(pid, 15)
                    # brief wait
                    time.sleep(0.5)
                    # optional force kill if still alive
                    try:
                        os.kill(pid, 0)
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
        sd = entry.get("storage_dir")
        if not sd:
            raise RuntimeError("bot has no storage directory")
        req = os.path.join(sd, "meshchatx_request_announce")
        try:
            with open(req, "w", encoding="utf-8") as f:
                f.write("1")
        except OSError as exc:
            logger.warning("Failed to write announce request: %s", exc)
            raise RuntimeError("failed to write announce request") from exc
        return True

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
            # Delete storage dir
            storage_dir = entry.get("storage_dir")
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

    def get_bot_identity_path(self, bot_id):
        entry = None
        for e in self.bots_state:
            if e.get("id") == bot_id:
                entry = e
                break

        if not entry:
            return None

        storage_dir = entry.get("storage_dir")
        if not storage_dir:
            return None

        bot_config_dir = entry.get("bot_config_dir")
        if bot_config_dir:
            id_path_bot_cfg = os.path.join(bot_config_dir, "identity")
            if os.path.exists(id_path_bot_cfg):
                return id_path_bot_cfg
            id_path_lxmf_cfg = os.path.join(bot_config_dir, "lxmf", "identity")
            if os.path.exists(id_path_lxmf_cfg):
                return id_path_lxmf_cfg

        reticulum_config_dir = entry.get("reticulum_config_dir")
        if reticulum_config_dir:
            id_path_shared = os.path.join(reticulum_config_dir, "identity")
            if os.path.exists(id_path_shared):
                return id_path_shared

        # LXMFy stores identity in the 'config' subdirectory by default
        id_path = os.path.join(storage_dir, "config", "identity")
        if os.path.exists(id_path):
            return id_path

        # Fallback to direct identity file if it was moved or configured differently
        id_path_alt = os.path.join(storage_dir, "identity")
        if os.path.exists(id_path_alt):
            return id_path_alt

        # LXMFy may nest inside config/lxmf
        id_path_lxmf = os.path.join(storage_dir, "config", "lxmf", "identity")
        if os.path.exists(id_path_lxmf):
            return id_path_lxmf

        id_path_lxmf_root = os.path.join(storage_dir, "lxmf", "identity")
        if os.path.exists(id_path_lxmf_root):
            return id_path_lxmf_root

        return None

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
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

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
