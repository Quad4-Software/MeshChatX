# SPDX-License-Identifier: 0BSD

"""Degrade RNS backbone clients to TCPClientInterface where epoll is missing.

RNS 1.5.4's BackboneClientInterface registers its socket into the shared
BackboneInterface epoll loop, which only exists on Linux and Android. On
macOS and Windows the registration raises
``module 'select' has no attribute 'epoll'``, the socket is dropped, and
the interface retries every five seconds forever. This hits both manually
configured ``type = BackboneInterface`` interfaces with a target_host or
remote, and interfaces auto-connected from interface discovery announces,
which is why autodiscovery on macOS spawns hundreds of dead interfaces.

Upstream already degrades the same endpoints in the config entries it
generates for discovered interfaces on non-Linux systems, and the wire
protocol is identical: both client classes speak HDLC-framed RNS packets
over TCP, so a TCPClientInterface can connect to a BackboneInterface
listener. This module performs the same degradation at construction time
by rebinding the BackboneClientInterface module attribute to
TCPClientInterface when platformutils.use_epoll() is false, matching the
gate LocalInterface already uses for its own backend selection.

The BackboneInterface listener class is not patched: it raises a clear
OSError on non-Linux platforms, which startup recovery handles.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_PATCHED = False
_ORIGINAL_CLIENT_CLASS = None


def _epoll_supported() -> bool:
    try:
        import RNS

        return bool(RNS.vendor.platformutils.use_epoll())
    except Exception:
        pass
    try:
        import select

        return hasattr(select, "epoll")
    except Exception:
        return False


def install_rns_backbone_patches() -> bool:
    """Rebind BackboneClientInterface to TCPClientInterface without epoll.

    No-op on Linux and Android where the shared epoll loop works.
    Idempotent. Returns True when the degradation was applied.
    """
    global _PATCHED, _ORIGINAL_CLIENT_CLASS
    if _PATCHED:
        return True
    if _epoll_supported():
        return False
    try:
        from RNS.Interfaces import BackboneInterface as backbone_module
        from RNS.Interfaces import TCPInterface as tcp_module
    except ImportError:
        return False

    _ORIGINAL_CLIENT_CLASS = backbone_module.BackboneClientInterface
    backbone_module.BackboneClientInterface = tcp_module.TCPClientInterface
    _PATCHED = True
    logger.info(
        "No epoll on this platform; degraded BackboneClientInterface to "
        "TCPClientInterface for backbone client connections",
    )
    return True
