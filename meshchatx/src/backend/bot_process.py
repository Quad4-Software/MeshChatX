import argparse
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
    args = parser.parse_args()

    os.makedirs(args.storage, exist_ok=True)
    os.chdir(args.storage)

    BotCls = TEMPLATE_MAP[args.template]
    # LXMFy hardcodes its config directory to os.path.join(os.getcwd(), 'config').
    # By chdir'ing into args.storage, we ensure 'config' and data are kept within that folder.
    bot_instance = BotCls(name=args.name, storage_path=args.storage, test_mode=False)

    # Optional immediate announce for reachability
    try:
        if hasattr(bot_instance.bot, "announce_enabled"):
            bot_instance.bot.announce_enabled = True
        if hasattr(bot_instance.bot, "_announce"):
            bot_instance.bot._announce()
    except Exception:
        pass

    bot_instance.run()


if __name__ == "__main__":
    main()
