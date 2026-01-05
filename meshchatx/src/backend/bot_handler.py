import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid

import RNS

logger = logging.getLogger("meshchatx.bots")


class BotHandler:
    def __init__(self, identity_path, config_manager=None):
        self.identity_path = os.path.abspath(identity_path)
        self.config_manager = config_manager
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
        except FileNotFoundError:
            self.bots_state = []
        except Exception:
            self.bots_state = []

    def _save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.bots_state, f, indent=2)
        except Exception:
            pass

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

    def get_status(self):
        bots = []
        for bot_id, bot_info in self.running_bots.items():
            instance = bot_info["instance"]
            bots.append(
                {
                    "id": bot_id,
                    "template": bot_info["template"],
                    "name": instance.bot.config.name
                    if instance and instance.bot
                    else "Unknown",
                    "address": RNS.prettyhexrep(instance.bot.local.hash)
                    if instance and instance.bot and instance.bot.local
                    else "Unknown",
                    "full_address": RNS.hexrep(instance.bot.local.hash, delimit=False)
                    if instance and instance.bot and instance.bot.local
                    else None,
                },
            )

        return {
            "has_lxmfy": True,
            "detection_error": None,
            "running_bots": bots,
            "bots": self.bots_state,
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
                "enabled": True,
                "pid": None,
            }
            self.bots_state.append(entry)
        else:
            bot_storage_dir = entry["storage_dir"]
            entry["template_id"] = template_id
            entry["name"] = name or entry.get("name") or f"{template_id.title()} Bot"
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
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
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
                        "Failed to delete storage dir for bot %s: %s", bot_id, exc
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

        # LXMFy stores identity in the 'config' subdirectory by default
        id_path = os.path.join(storage_dir, "config", "identity")
        if os.path.exists(id_path):
            return id_path

        # Fallback to direct identity file if it was moved or configured differently
        id_path_alt = os.path.join(storage_dir, "identity")
        if os.path.exists(id_path_alt):
            return id_path_alt

        return None

    def stop_all(self):
        for bot_id in list(self.running_bots.keys()):
            self.stop_bot(bot_id)
