"""RRC room bot template that joins hubs and echoes mentions."""

from __future__ import annotations

from lxmfy import LXMFBot, RRCMessage

DEFAULT_RRC_HUB = "664fc0e8d2e448658e37bb3f34e6c88f"
DEFAULT_RRC_ROOMS = ["general"]


class RRCBot:
    """Bot that participates in Reticulum Relay Chat rooms."""

    def __init__(
        self,
        hubs: list[str] | None = None,
        rooms: list[str] | None = None,
        nick: str | None = None,
        test_mode: bool = False,
        reticulum_config_dir: str | None = None,
    ):
        """Initialize an RRC-capable bot.

        Args:
            hubs: Hub destination hashes (hex) to join on startup.
            rooms: Rooms to auto-join after WELCOME.
            nick: Nickname advertised on HELLO and room messages.
            test_mode: Skip RNS initialization when True.
            reticulum_config_dir: Optional Reticulum config directory override.

        """
        resolved_hubs = list(hubs) if hubs is not None else [DEFAULT_RRC_HUB]
        resolved_rooms = list(rooms) if rooms is not None else list(DEFAULT_RRC_ROOMS)
        self.bot = LXMFBot(
            name=nick or "RRC Bot",
            announce=600,
            announce_enabled=True,
            first_message_enabled=True,
            test_mode=test_mode,
            reticulum_config_dir=reticulum_config_dir,
            rrc_enabled=bool(resolved_hubs) and not test_mode,
            rrc_hubs=resolved_hubs,
            rrc_rooms=resolved_rooms,
            rrc_nick=nick or "RRCBot",
            rrc_auto_reconnect=True,
        )
        self.setup_handlers()

    def setup_handlers(self) -> None:
        """Register LXMF and RRC handlers."""

        @self.bot.on_first_message()
        def welcome(sender, message):
            self.bot.send(
                sender,
                "RRC bot online. I join configured hubs and reply to @mentions in rooms.",
            )
            return True

        @self.bot.on_rrc
        def on_rrc(event, client, payload):
            if event == "welcome":
                self.bot.logger.info(
                    "RRC welcomed by %s",
                    payload.get("hub_name") if isinstance(payload, dict) else "hub",
                )
                return
            if event != "msg" or not isinstance(payload, RRCMessage):
                return
            if payload.mention and payload.room:
                reply = f"{payload.nick or 'someone'} mentioned me: {payload.text}"
                try:
                    client.send_message(payload.room, reply)
                except Exception as exc:
                    self.bot.logger.error("RRC reply failed: %s", exc)

    def run(self) -> None:
        """Run the bot event loop."""
        self.bot.run()
