# SPDX-License-Identifier: 0BSD
"""Vulture whitelist for protocol-required names.

These names are required by external callback protocols even when a given
implementation does not use them: RNS request responder signatures receive a
requested_at timestamp, context manager exit methods receive exception
details, and Chaquopy hotspot callbacks receive the security type. Vulture
only counts name occurrences, so referencing the names here marks them as
used project-wide.
"""

from aiohttp import WSMessage


def _whitelist_protocol_names() -> list:
    # WSMessage is only referenced through string-literal forward references
    # in cast() calls, which vulture does not count as usage.
    return [requested_at, exc_type, exc_val, exc_tb, security_type, WSMessage]  # noqa: F821
