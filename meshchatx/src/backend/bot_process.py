# SPDX-License-Identifier: 0BSD

import argparse
import contextlib
import os
import signal
import threading
import time
import traceback

from meshchatx.src.backend.bot_lxmf_config import load_bot_lxmf_config_sidecar
from meshchatx.src.backend.bot_options import load_bot_runtime_sidecar
from meshchatx.src.backend.bot_templates import (
    CustomBotTemplate,
    EchoBotTemplate,
    NoteBotTemplate,
    ReminderBotTemplate,
    RRCBotTemplate,
)

TEMPLATE_MAP = {
    "echo": EchoBotTemplate,
    "note": NoteBotTemplate,
    "reminder": ReminderBotTemplate,
    "custom": CustomBotTemplate,
    "rrc": RRCBotTemplate,
}


def _parent_watchdog(parent_pid):
    """Exit when the MeshChatX backend that spawned this bot is gone.

    Bots run in their own session, so terminal Ctrl+C never reaches them.
    They rely on the backend calling stop_all; if the backend dies without
    cleanup (SIGKILL, os._exit, a test runner exiting) they would otherwise
    reparent to init and run forever.
    """
    while True:
        time.sleep(1.0)
        try:
            if os.getppid() != parent_pid:
                break
        except OSError:
            break
        try:
            os.kill(parent_pid, 0)
        except OSError:
            break
    with contextlib.suppress(Exception):
        print("meshchatx bot exiting: parent process gone", flush=True)
    # SIGTERM first so RNS exit handlers can flush, then a hard backstop in
    # case no handler is installed or it hangs.
    with contextlib.suppress(Exception):
        os.kill(os.getpid(), signal.SIGTERM)
    time.sleep(2.0)
    os._exit(0)


def _control_watcher(bot_instance, storage_dir):
    """MeshChatX trigger file for on-demand announces (LXMFy reads bot_display_name.txt in config)."""
    announce_req = os.path.join(storage_dir, "meshchatx_request_announce")
    while True:
        time.sleep(0.6)
        try:
            if os.path.isfile(announce_req):
                os.unlink(announce_req)
                if hasattr(bot_instance.bot, "announce_now"):
                    bot_instance.bot.announce_now(force=True)
                elif hasattr(bot_instance.bot, "_announce"):
                    bot_instance.bot._announce()
        except OSError:
            pass
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, choices=TEMPLATE_MAP.keys())
    parser.add_argument("--name", required=True)
    parser.add_argument("--storage", required=True)
    parser.add_argument("--config-path", default=None)
    parser.add_argument(
        "--reticulum-config-dir",
        default=os.environ.get(
            "MESHCHAT_BOT_RETICULUM_CONFIG_DIR",
            os.path.expanduser("~/.reticulum"),
        ),
    )
    parser.add_argument("--lxmf-config-file", default=None)
    parser.add_argument("--runtime-config-file", default=None)
    parser.add_argument("--rrc-hub", default=None)
    parser.add_argument("--rrc-rooms", default="")
    parser.add_argument("--rrc-nick", default=None)
    parser.add_argument("--rrc-mention-only", type=int, choices=(0, 1), default=1)
    parser.add_argument("--rrc-prefix", default="!")
    parser.add_argument("--rrc-rate", type=int, default=8)
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=None,
        help="PID of the spawning MeshChatX backend; bot exits when it dies",
    )
    args = parser.parse_args()

    # A bot must never outlive the backend. The explicit --parent-pid arg beats
    # getppid because the parent can die before this interpreter finishes
    # starting, leaving the bot already reparented at capture time. A manual
    # bot_process run without the flag falls back to watching its launcher.
    parent_pid = args.parent_pid or os.getppid()
    if parent_pid and parent_pid > 1:
        threading.Thread(
            target=_parent_watchdog,
            args=(parent_pid,),
            daemon=True,
            name="meshchatx-bot-parent-watchdog",
        ).start()

    storage_abs = os.path.abspath(args.storage)
    err_path = os.path.join(storage_abs, "meshchatx_bot_last_error.txt")
    with contextlib.suppress(OSError):
        os.unlink(err_path)

    os.makedirs(args.storage, exist_ok=True)

    config_path = args.config_path
    if config_path:
        config_path = os.path.abspath(os.path.expanduser(config_path))
    else:
        config_path = os.path.join(os.path.abspath(args.storage), "config")
    os.makedirs(config_path, exist_ok=True)
    reticulum_config_dir = os.path.abspath(
        os.path.expanduser(args.reticulum_config_dir),
    )
    os.makedirs(reticulum_config_dir, exist_ok=True)

    lxmf_settings = load_bot_lxmf_config_sidecar(args.lxmf_config_file)
    runtime_opts = load_bot_runtime_sidecar(args.runtime_config_file)

    template_kwargs = {}
    if "icon" in runtime_opts:
        template_kwargs["icon"] = runtime_opts["icon"]
    if args.template == "custom":
        template_kwargs["custom"] = runtime_opts.get("custom")
    if args.template == "rrc":
        template_kwargs = {
            "rrc_hub": args.rrc_hub,
            "rrc_rooms": [
                r.strip() for r in (args.rrc_rooms or "").split(",") if r.strip()
            ],
            "rrc_nick": args.rrc_nick,
            "rrc_mention_only": bool(args.rrc_mention_only),
            "rrc_command_prefix": args.rrc_prefix,
            "rrc_rate_seconds": args.rrc_rate,
        }

    try:
        BotCls = TEMPLATE_MAP[args.template]
        bot_instance = BotCls(
            name=args.name,
            storage_path=args.storage,
            test_mode=False,
            config_path=config_path,
            reticulum_config_dir=reticulum_config_dir,
            lxmf_settings=lxmf_settings,
            **template_kwargs,
        )
    except BaseException:
        try:
            with open(err_path, "w", encoding="utf-8") as ef:
                traceback.print_exc(file=ef)
        except OSError:
            pass
        raise
    with (
        contextlib.suppress(OSError),
        open(
            os.path.join(config_path, "bot_display_name.txt"),
            "w",
            encoding="utf-8",
        ) as f,
    ):
        f.write(args.name.strip())

    watcher = threading.Thread(
        target=_control_watcher,
        args=(bot_instance, storage_abs),
        daemon=True,
        name="meshchatx-bot-control",
    )
    watcher.start()

    with contextlib.suppress(Exception):
        local = getattr(bot_instance.bot, "local", None)
        if local is not None:
            raw = getattr(local, "hash", None)
            if raw is not None:
                hx = raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw)
                hx = hx.strip().lower()
                if len(hx) == 32:
                    sidecar = os.path.join(storage_abs, "meshchatx_lxmf_address.txt")
                    with open(sidecar, "w", encoding="utf-8") as f:
                        f.write(hx)

    # Optional immediate announce for reachability
    with contextlib.suppress(Exception):
        if hasattr(bot_instance.bot, "announce_enabled"):
            bot_instance.bot.announce_enabled = True
        if hasattr(bot_instance.bot, "announce_now"):
            bot_instance.bot.announce_now(force=True)
        elif hasattr(bot_instance.bot, "_announce"):
            bot_instance.bot._announce()

    try:
        bot_instance.run()
    except BaseException:
        try:
            with open(err_path, "w", encoding="utf-8") as ef:
                traceback.print_exc(file=ef)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
