# Sideband command plugin for RNS FileSync.
#
# Drop this file into Sideband's plugins directory and enable command plugins.
# Requires the matching service plugin (rns_filesync_service.py) to be loaded.
#
# LXMF usage examples (from a trusted peer that can send commands):
#   filesync status
#   filesync peers
#   filesync files
#   filesync announce
#   filesync connect <identity_hash>
#   filesync disconnect <peer_id>

from __future__ import annotations

import RNS


class RnsFilesyncCommandPlugin(SidebandCommandPlugin):
    command_name = "filesync"

    def start(self):
        RNS.log("RNS FileSync Sideband command plugin starting...", RNS.LOG_NOTICE)
        super().start()

    def stop(self):
        super().stop()

    def _reply(self, text: str, destination):
        self.get_sideband().send_message(
            text,
            destination,
            False,
            skip_fields=True,
            no_display=True,
        )

    def _get_service(self):
        sideband = self.get_sideband()
        plugins = getattr(sideband, "active_service_plugins", {}) or {}
        plugin = plugins.get("rns_filesync")
        if plugin is None:
            return None
        getter = getattr(plugin, "get_filesync", None)
        if callable(getter):
            return getter()
        return getattr(plugin, "service", None)

    def handle_command(self, arguments, lxm):
        requestor = lxm.source_hash
        args = [str(a) for a in (arguments or [])]
        if not args:
            self._reply(
                "Usage: filesync status|peers|files|announce|"
                "connect <hash>|disconnect <id>",
                requestor,
            )
            return

        service = self._get_service()
        if service is None:
            self._reply(
                "RNS FileSync service is not running. "
                "Enable service plugins and install rns_filesync_service.py.",
                requestor,
            )
            return

        cmd = args[0].lower()
        try:
            if cmd == "status":
                status = service.get_status()
                lines = [f"{key}={value}" for key, value in status.items()]
                self._reply("\n".join(lines), requestor)
            elif cmd == "peers":
                peers = service.list_peers()
                if not peers:
                    self._reply("No connected peers", requestor)
                    return
                lines = []
                for peer in peers:
                    lines.append(
                        f"{peer.get('peer_id')} status={peer.get('status')} "
                        f"dest={peer.get('destination_hash')}",
                    )
                self._reply("\n".join(lines), requestor)
            elif cmd == "files":
                files = service.list_files()
                if not files:
                    self._reply("No files in sync inventory", requestor)
                    return
                lines = [
                    f"{item.get('path')}\t{item.get('size')}\t{item.get('hash')}"
                    for item in files
                ]
                self._reply("\n".join(lines), requestor)
            elif cmd == "announce":
                service.announce_now()
                self._reply("Announced", requestor)
            elif cmd == "connect" and len(args) >= 2:
                result = service.connect_peer(args[1])
                self._reply(str(result), requestor)
            elif cmd == "disconnect" and len(args) >= 2:
                service.disconnect_peer(args[1])
                self._reply(f"Disconnected {args[1]}", requestor)
            else:
                self._reply(
                    "Unknown command. Use: status peers files announce "
                    "connect <hash> disconnect <id>",
                    requestor,
                )
        except Exception as exc:
            RNS.log(f"filesync command error: {exc}", RNS.LOG_ERROR)
            self._reply(f"Error: {exc}", requestor)


plugin_class = RnsFilesyncCommandPlugin
