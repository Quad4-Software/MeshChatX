# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: user_guidance."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


def build_user_guidance_messages(app: Any):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    guidance = []

    interfaces = app._get_interfaces_section()
    if len(interfaces) == 0:
        guidance.append(
            {
                "id": "no_interfaces",
                "title": "No Reticulum interfaces configured",
                "description": "Add at least one Reticulum interface so MeshChat can talk to your radio or transport.",
                "action_route": "/interfaces/add",
                "action_label": "Add Interface",
                "severity": "warning",
            },
        )

    failed_autointerfaces = app._detect_failed_autointerfaces()
    if failed_autointerfaces:
        failed_label = ", ".join(failed_autointerfaces)
        guidance.append(
            {
                "id": "autointerface_bind_failed",
                "title": "AutoInterface failed to start",
                "description": (
                    f"AutoInterface '{failed_label}' is enabled in your "
                    "Reticulum config but did not come up at runtime. "
                    "The most common cause is a UDP port collision with "
                    "another local Reticulum application (for example "
                    "Sideband running on the same device on Android). "
                    "Open the interface and set a unique group_id, or "
                    "pick free discovery_port and data_port values, then "
                    "restart Reticulum."
                ),
                "action_route": "/interfaces",
                "action_label": "Open Interfaces",
                "severity": "warning",
            },
        )

    if (
        hasattr(self, "reticulum")
        and app.reticulum
        and not app.reticulum.transport_enabled()
    ):
        guidance.append(
            {
                "id": "transport_disabled",
                "title": "Transport mode is disabled",
                "description": "Enable transport to allow MeshChat to relay traffic over your configured interfaces.",
                "action_route": "/settings",
                "action_label": "Open Settings",
                "severity": "info",
            },
        )

    if not app.config.auto_announce_enabled.get():
        guidance.append(
            {
                "id": "announce_disabled",
                "title": "Auto announcements are turned off",
                "description": "Automatic announces make it easier for other peers to discover you. Enable them if you want to stay visible.",
                "action_route": "/settings",
                "action_label": "Manage Announce Settings",
                "severity": "info",
            },
        )

    return guidance
