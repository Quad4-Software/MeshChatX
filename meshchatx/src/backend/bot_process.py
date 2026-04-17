# SPDX-License-Identifier: 0BSD

import argparse
import contextlib
import os
import threading
import time

from meshchatx.src.backend.bot_templates import (
    EchoBotTemplate,
    NoteBotTemplate,
    ReminderBotTemplate,
)

TEMPLATE_MAP = {
    "echo": EchoBotTemplate,
    "note": NoteBotTemplate,
    "reminder": ReminderBotTemplate,
}


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
    args = parser.parse_args()

    os.makedirs(args.storage, exist_ok=True)

    config_path = args.config_path
    if config_path:
        config_path = os.path.abspath(os.path.expanduser(config_path))
    else:
        config_path = os.path.join(os.path.abspath(args.storage), "config")
    os.makedirs(config_path, exist_ok=True)
    reticulum_config_dir = os.path.abspath(
        os.path.expanduser(args.reticulum_config_dir)
    )
    os.makedirs(reticulum_config_dir, exist_ok=True)

    BotCls = TEMPLATE_MAP[args.template]
    bot_instance = BotCls(
        name=args.name,
        storage_path=args.storage,
        test_mode=False,
        config_path=config_path,
        reticulum_config_dir=reticulum_config_dir,
    )

    storage_abs = os.path.abspath(args.storage)
    with contextlib.suppress(OSError):
        with open(
            os.path.join(config_path, "bot_display_name.txt"),
            "w",
            encoding="utf-8",
        ) as f:
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

    bot_instance.run()


if __name__ == "__main__":
    main()
