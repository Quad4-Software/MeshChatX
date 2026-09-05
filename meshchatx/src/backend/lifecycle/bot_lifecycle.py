# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: bot_lifecycle."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


def check_bot_lifecycle(app: Any) -> tuple[bool, str]:
    """Create, start, stop, and delete an Echo bot subprocess.

    Uses an isolated identity + Reticulum config under storage so the check
    does not touch user bots or ~/.reticulum.
    """
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    from meshchatx.src.backend.bot_handler import BotHandler

    if not app.storage_path or not os.path.exists(app.storage_path):
        return False, "Storage directory does not exist"

    root = os.path.join(app.storage_path, ".self_test_bots")
    identity_dir = os.path.join(root, "identity")
    rns_dir = os.path.join(root, "reticulum")
    bot_id = None
    handler = None
    try:
        if os.path.isdir(root):
            shutil.rmtree(root, ignore_errors=True)
        os.makedirs(identity_dir, exist_ok=True)
        os.makedirs(rns_dir, exist_ok=True)

        previous_rns = os.environ.get("MESHCHAT_BOT_RETICULUM_CONFIG_DIR")
        os.environ["MESHCHAT_BOT_RETICULUM_CONFIG_DIR"] = rns_dir
        try:
            handler = BotHandler(identity_path=identity_dir)
            bot_id = handler.start_bot("echo", "Self-Check Echo Bot")
        finally:
            if previous_rns is None:
                os.environ.pop("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", None)
            else:
                os.environ["MESHCHAT_BOT_RETICULUM_CONFIG_DIR"] = previous_rns

        entry = next(
            (e for e in handler.bots_state if e.get("id") == bot_id),
            None,
        )
        if entry is None:
            return False, "Bot entry missing after start"

        pid = entry.get("pid")
        if not pid:
            return False, "Bot process did not report a pid"

        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            if not BotHandler._is_pid_alive(pid):
                last_err = BotHandler._read_bot_last_error(entry.get("storage_dir"))
                log_tail = ""
                try:
                    log_info = handler.read_subprocess_log(bot_id, max_bytes=2048)
                    log_tail = (log_info.get("log") or "").strip()[-500:]
                except Exception:
                    pass
                detail = last_err or log_tail or "process exited early"
                return False, f"Bot process died after start: {detail}"
            # Confirm the launcher wrote something (script or run-module path).
            try:
                log_info = handler.read_subprocess_log(bot_id, max_bytes=1024)
                if log_info.get("total_bytes", 0) > 0:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            if not BotHandler._is_pid_alive(pid):
                return False, "Bot process exited before becoming ready"
            # Still alive with empty log is acceptable (buffered / slow start).

        if not handler.stop_bot(bot_id):
            return False, "stop_bot returned False"
        stop_deadline = time.monotonic() + 8.0
        while time.monotonic() < stop_deadline and BotHandler._is_pid_alive(pid):
            time.sleep(0.1)
        if BotHandler._is_pid_alive(pid):
            return False, f"Bot pid {pid} still alive after stop"

        storage_dir = entry.get("storage_dir")
        if not handler.delete_bot(bot_id):
            return False, "delete_bot returned False"
        if any(e.get("id") == bot_id for e in handler.bots_state):
            return False, "Bot still present in state after delete"
        if storage_dir and os.path.exists(storage_dir):
            return False, "Bot storage directory still exists after delete"

        return True, ""
    except Exception as e:
        return False, f"Bot lifecycle check failed: {e}"
    finally:
        if handler is not None and bot_id is not None:
            with contextlib.suppress(Exception):
                handler.stop_bot(bot_id)
            with contextlib.suppress(Exception):
                handler.delete_bot(bot_id)
        with contextlib.suppress(Exception):
            if os.path.isdir(root):
                shutil.rmtree(root, ignore_errors=True)
