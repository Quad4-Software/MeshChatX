# SPDX-License-Identifier: 0BSD

import argparse
import contextlib
import os

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

    # Optional immediate announce for reachability
    with contextlib.suppress(Exception):
        if hasattr(bot_instance.bot, "announce_enabled"):
            bot_instance.bot.announce_enabled = True
        if hasattr(bot_instance.bot, "_announce"):
            bot_instance.bot._announce()

    bot_instance.run()


if __name__ == "__main__":
    main()
