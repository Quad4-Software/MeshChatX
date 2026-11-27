# SPDX-License-Identifier: 0BSD
"""Vulture whitelist for protocol-required names.

These names are required by external callback protocols even when a given
implementation does not use them: RNS request responder signatures receive a
requested_at timestamp, context manager exit methods receive exception
details, and Chaquopy hotspot callbacks receive the security type. Vulture
only counts name occurrences, so referencing the names here marks them as
used project-wide.
"""


def _whitelist_protocol_names() -> list:
    return [requested_at, exc_type, exc_val, exc_tb, security_type]  # noqa: F821
