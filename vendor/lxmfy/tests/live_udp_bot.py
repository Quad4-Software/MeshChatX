"""Bot worker for the live UDP pair test.

Run by test_live_udp_pair.py as a subprocess so it gets a private
Reticulum instance. Writes the delivery destination hash to the ready
file, then serves /ping and attachment acknowledgements.
"""

import sys
from pathlib import Path


def main() -> None:
    config_dir = Path(sys.argv[1])
    ready_file = Path(sys.argv[2])

    import LXMF
    import RNS
    from LXMF import LXMessage

    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="UDPTestBot",
        test_mode=False,
        config_path=str(config_dir / "botcfg"),
        storage_path=str(config_dir / "botdata"),
        storage_type="json",
        reticulum_config_dir=str(config_dir),
        announce_enabled=True,
        announce_immediately=True,
        first_message_enabled=False,
        landlock_enabled=False,
        cogs_enabled=False,
        signature_verification_enabled=False,
        propagation_fallback_enabled=False,
        message_persistence_enabled=False,
        loglevel=4,
    )

    @bot.command("ping")
    def ping(msg):
        token = msg.args[0] if msg.args else "none"
        msg.reply(f"pong:{token}")

    @bot.on_message()
    def on_msg(sender, message):
        fields = getattr(message, "fields", None) or {}
        files = fields.get(LXMF.FIELD_FILE_ATTACHMENTS)
        if isinstance(files, list) and files:
            name, data = files[0]
            size = len(data) if isinstance(data, bytes) else 0
            bot.send(
                sender,
                f"file_ok:{name}:{size}",
                title="FileAck",
                method=LXMessage.OPPORTUNISTIC,
            )
            return True
        return False

    ready_file.write_text(
        RNS.hexrep(bot.local.hash, delimit=False),
        encoding="utf-8",
    )
    bot.run(delay=0.2)


if __name__ == "__main__":
    main()
