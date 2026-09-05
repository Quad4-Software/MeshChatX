# SPDX-License-Identifier: 0BSD
"""Permissions-Policy tokens must stay quiet on Chrome, Brave, Firefox, Safari."""

from __future__ import annotations

from meshchatx.src.backend.http.middleware import (
    _PERMISSIONS_POLICY_CORE,
    build_permissions_policy,
)

# Tokens that historically caused Brave/Chrome "Unrecognized feature" noise when
# listed, while MDN defaults already allow them for same-origin documents.
_HARDWARE_AND_FLAGGED = (
    "bluetooth",
    "serial",
    "usb",
    "hid",
    "speaker-selection",
)


def test_permissions_policy_core_tokens_only():
    policy = build_permissions_policy()
    assert policy == "microphone=(self), camera=(self), autoplay=(self)"
    assert set(_PERMISSIONS_POLICY_CORE) == {
        "microphone=(self)",
        "camera=(self)",
        "autoplay=(self)",
    }
    lower = policy.lower()
    for token in _HARDWARE_AND_FLAGGED:
        assert token not in lower


def test_permissions_policy_does_not_emit_legacy_feature_policy_name():
    # Guard against regressing to Feature-Policy in the builder helpers.
    assert "feature-policy" not in build_permissions_policy().lower()
