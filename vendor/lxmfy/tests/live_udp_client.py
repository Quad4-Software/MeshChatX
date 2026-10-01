"""Client worker for the live UDP pair test.

Run by test_live_udp_pair.py as a subprocess. Uses a raw LXMRouter
(rather than LXMFBot) so the bot is exercised as a real protocol peer.
Sends a /ping command and a file attachment with DIRECT delivery, which
forces link-based transfer, then reports replies over the result file.
"""

import json
import sys
import time
from pathlib import Path


def main() -> None:
    config_dir = Path(sys.argv[1])
    bot_hash_hex = sys.argv[2]
    result_file = Path(sys.argv[3])

    import LXMF
    import RNS
    from LXMF import LXMessage, LXMRouter

    RNS.Reticulum(configdir=str(config_dir))
    identity = RNS.Identity()
    router = LXMRouter(
        identity=identity,
        storagepath=str(config_dir / "lxmf"),
        autopeer=False,
    )
    local = router.register_delivery_identity(identity, display_name="UDPTestClient")

    received = []

    def on_message(message):
        content = message.content.decode("utf-8") if message.content else ""
        received.append(
            {
                "sender": RNS.hexrep(message.source_hash, delimit=False),
                "content": content,
                "title": message.title.decode("utf-8") if message.title else "",
                "signature_validated": bool(
                    getattr(message, "signature_validated", False)
                ),
            },
        )

    router.register_delivery_callback(on_message)
    local.announce()

    bot_hash = bytes.fromhex(bot_hash_hex)
    bot_identity = None
    deadline = time.time() + 45
    while time.time() < deadline:
        bot_identity = RNS.Identity.recall(bot_hash)
        if bot_identity is not None and RNS.Transport.has_path(bot_hash):
            break
        RNS.Transport.request_path(bot_hash)
        time.sleep(0.4)

    result = {"error": None, "pong": None, "file_ack": None}
    if bot_identity is None:
        result["error"] = "bot identity never learned"
        result_file.write_text(json.dumps(result), encoding="utf-8")
        return

    bot_dest = RNS.Destination(
        bot_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )

    token = "tok123"
    ping = LXMessage(
        bot_dest,
        local,
        f"/ping {token}".encode(),
        title=b"Ping",
        desired_method=LXMessage.DIRECT,
    )
    router.handle_outbound(ping)

    file_msg = LXMessage(
        bot_dest,
        local,
        b"file note",
        title=b"File",
        desired_method=LXMessage.DIRECT,
        fields={LXMF.FIELD_FILE_ATTACHMENTS: [["note.txt", b"payload-bytes"]]},
    )
    router.handle_outbound(file_msg)

    deadline = time.time() + 45
    while time.time() < deadline:
        for entry in received:
            if entry["content"] == f"pong:{token}":
                result["pong"] = entry
            if entry["content"].startswith("file_ok:note.txt:13"):
                result["file_ack"] = entry
        if result["pong"] and result["file_ack"]:
            break
        time.sleep(0.3)

    result_file.write_text(json.dumps(result), encoding="utf-8")


if __name__ == "__main__":
    main()
