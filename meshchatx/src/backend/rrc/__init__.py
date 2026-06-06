# SPDX-License-Identifier: 0BSD

"""Reticulum Relay Chat (RRC) implementation for MeshChatX.

This package provides a wire-compatible client for RRC hubs (rrcd) and the
ability to host hubs locally. The protocol layer in :mod:`protocol` is free of
any Reticulum dependency so the encoding rules and parsers can be unit tested in
isolation. :mod:`manager` contains the client link handling and session state,
while :mod:`server` hosts one or more local hubs built on the Reticulum Network
Stack.
"""

from meshchatx.src.backend.rrc.manager import RRCManager
from meshchatx.src.backend.rrc.protocol import RRCMessage
from meshchatx.src.backend.rrc.server import RRCHubServer, RRCServerManager

__all__ = ["RRCHubServer", "RRCManager", "RRCMessage", "RRCServerManager"]
