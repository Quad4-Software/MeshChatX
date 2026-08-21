# SPDX-License-Identifier: 0BSD

"""Deferred network startup helpers.

Thin wrappers live on ReticulumMeshChat. Business steps stay here so
identity and RNS lifecycle stay reviewable outside meshchat.py.
"""

from __future__ import annotations

import json
import traceback

from meshchatx.src.backend.async_utils import AsyncUtils


def run_network_setup(app) -> None:
    """Run identity setup and publish network_ready or degraded status."""
    identity = app._pending_identity
    if identity is None:
        app._set_startup_stage("failed", "No identity available for network setup")
        return
    try:
        app.setup_identity(identity)
        if app.config is not None and getattr(app, "session_secret_key", None):
            try:
                app.config.auth_session_secret.set(app.session_secret_key)
            except Exception as exc:
                print(f"Failed to persist session secret into config: {exc}")
        app._mark_network_ready()
        finish_deferred_startup_services(app)
        print("Network stack ready", flush=True)
        if app.websocket_clients:
            try:
                AsyncUtils.run_async(
                    app.websocket_broadcast(
                        json.dumps(
                            {
                                "type": "startup_status",
                                "status": "ok",
                                "stage": "ready",
                                "network_ready": True,
                            },
                        ),
                    ),
                )
            except Exception:
                pass
    except Exception as exc:
        traceback.print_exc()
        app._mark_network_degraded(str(exc))
        if app.websocket_clients:
            try:
                AsyncUtils.run_async(
                    app.websocket_broadcast(
                        json.dumps(
                            {
                                "type": "startup_status",
                                "status": "failed",
                                "stage": "failed",
                                "network_ready": False,
                                "network_degraded": True,
                                "ui_ready": True,
                                "error": str(exc),
                            },
                        ),
                    ),
                )
            except Exception:
                pass


def finish_deferred_startup_services(app) -> None:
    """Start non-critical services after network_ready is published."""
    context = app.current_context
    if context is not None:
        try:
            context.setup_deferred_services()
        except Exception as exc:
            print(f"Deferred identity services failed: {exc}", flush=True)
    start_deferred_reticulum_services(app)


def start_deferred_reticulum_services(app) -> None:
    if app._reticulum_secondary_started:
        return
    if not hasattr(app, "reticulum"):
        return
    app._reticulum_secondary_started = True
    try:
        app.page_node_manager.start_all()
        for node in app.page_node_manager.nodes.values():
            if node.running and node.destination:
                app._register_local_page_node_announce(node)
    except Exception as exc:
        print(f"Deferred page node start failed: {exc}", flush=True)
    if app.plugins_enabled:
        try:
            app.plugin_manager.install_bundled_examples()
        except Exception as exc:
            print(f"Bundled plugin sync failed: {exc}", flush=True)
    try:
        app.sideband_plugin_loader.reload()
        app._ensure_sideband_telemetry_loop()
    except Exception as exc:
        print(f"Sideband plugin loader init failed: {exc}")
