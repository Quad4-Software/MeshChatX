# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: update_config."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.map_overlay_manager import (
    CONFIG_CLAMPS,
    clamp_overlay_config_value,
)

# ruff: noqa: F821


async def apply_config_update(app: Any, data):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    g = mc.__dict__
    for _k in (
        "LXMF",
        "RNS",
        "AsyncUtils",
        "InterfaceEditor",
        "InterfaceConfigParser",
        "web",
        "json",
        "logger",
        "logging",
        "os",
        "sys",
        "time",
        "asyncio",
        "traceback",
        "copy",
        "shutil",
        "tempfile",
        "threading",
        "base64",
        "configparser",
        "sqlite3",
        "secrets",
        "re",
        "io",
        "contextlib",
        "datetime",
        "platform",
        "cast",
        "UTC",
    ):
        if _k in g:
            globals()[_k] = g[_k]
    # update display name in config
    if "display_name" in data and data["display_name"] != "":
        app.config.display_name.set(data["display_name"])
        # Update identity metadata cache
        app.update_identity_metadata_cache()

    # update theme in config
    if "theme" in data and data["theme"] != "":
        theme = data["theme"]
        if theme not in ("light", "dark", "system"):
            theme = "light"
        app.config.theme.set(theme)

    if "theme_preset" in data:
        preset = data["theme_preset"]
        if preset == "hister":
            preset = "neo_brutalist"
        if preset not in (
            "default",
            "high_contrast",
            "oled",
            "solarized",
            "nord",
            "gruvbox",
            "catppuccin",
            "dracula",
            "rose_pine",
            "forest",
            "midnight",
            "warm_paper",
            "tokyo",
            "atom_one",
            "neo_brutalist",
            "custom",
        ):
            preset = "default"
        app.config.theme_preset.set(preset)

    if "accent_color" in data:
        app.config.accent_color.set(
            app._normalize_optional_hex_color(data["accent_color"]),
        )

    if "custom_canvas_color" in data:
        app.config.custom_canvas_color.set(
            app._normalize_optional_hex_color(data["custom_canvas_color"]),
        )

    if "custom_surface_color" in data:
        app.config.custom_surface_color.set(
            app._normalize_optional_hex_color(data["custom_surface_color"]),
        )

    # update language in config
    if "language" in data and data["language"] != "":
        app.config.language.set(data["language"])

    # update auto announce interval
    if "auto_announce_interval_seconds" in data:
        # auto auto announce interval
        auto_announce_interval_seconds = app._coerce_int(
            data["auto_announce_interval_seconds"],
        )
        if auto_announce_interval_seconds is None:
            auto_announce_interval_seconds = (
                app.config.auto_announce_interval_seconds.get()
            )
        app.config.auto_announce_interval_seconds.set(
            auto_announce_interval_seconds,
        )

        # enable or disable auto announce based on interval
        if auto_announce_interval_seconds > 0:
            app.config.auto_announce_enabled.set(True)
        else:
            app.config.auto_announce_enabled.set(False)

    if "auto_resend_failed_messages_when_announce_received" in data:
        value = app._parse_bool(
            data["auto_resend_failed_messages_when_announce_received"],
        )
        app.config.auto_resend_failed_messages_when_announce_received.set(value)

    if "allow_auto_resending_failed_messages_with_attachments" in data:
        value = app._parse_bool(
            data["allow_auto_resending_failed_messages_with_attachments"],
        )
        app.config.allow_auto_resending_failed_messages_with_attachments.set(value)

    if "auto_send_failed_messages_to_propagation_node" in data:
        value = app._parse_bool(
            data["auto_send_failed_messages_to_propagation_node"],
        )
        app.config.auto_send_failed_messages_to_propagation_node.set(value)

    if "delivery_helptips_enabled" in data:
        value = app._parse_bool(data["delivery_helptips_enabled"])
        app.config.delivery_helptips_enabled.set(value)

    if "lxmf_delivery_transfer_limit_in_bytes" in data:
        value = app._coerce_int(data["lxmf_delivery_transfer_limit_in_bytes"])
        if value is None:
            value = app.config.lxmf_delivery_transfer_limit_in_bytes.get()
        value = max(1000, min(value, 1000 * 1000 * 1000))
        app.config.lxmf_delivery_transfer_limit_in_bytes.set(value)
        app.message_router.delivery_per_transfer_limit = value / 1000

    if "lxmf_propagation_transfer_limit_in_bytes" in data:
        value = app._coerce_int(data["lxmf_propagation_transfer_limit_in_bytes"])
        if value is None:
            value = app.config.lxmf_propagation_transfer_limit_in_bytes.get()
        value = max(1000, min(value, 1000 * 1000 * 100))
        app.config.lxmf_propagation_transfer_limit_in_bytes.set(value)
        app.message_router.propagation_per_transfer_limit = value / 1000
        if app.config.lxmf_local_propagation_node_enabled.get():
            app.message_router.announce_propagation_node()

    if "lxmf_propagation_sync_limit_in_bytes" in data:
        value = app._coerce_int(data["lxmf_propagation_sync_limit_in_bytes"])
        if value is None:
            value = app.config.lxmf_propagation_sync_limit_in_bytes.get()
        value = max(1000, min(value, 1000 * 1000 * 500))
        app.config.lxmf_propagation_sync_limit_in_bytes.set(value)
        app.message_router.propagation_per_sync_limit = value / 1000

    if "show_suggested_community_interfaces" in data:
        value = app._parse_bool(data["show_suggested_community_interfaces"])
        app.config.show_suggested_community_interfaces.set(value)

    _announce_int_fields = [
        ("announce_max_stored_lxmf_delivery", 1, 1_000_000),
        ("announce_max_stored_nomadnetwork_node", 1, 1_000_000),
        ("announce_max_stored_lxmf_propagation", 1, 1_000_000),
        ("announce_max_stored_map_data", 1, 1_000_000),
        ("announce_fetch_limit_lxmf_delivery", 1, 100_000),
        ("announce_fetch_limit_nomadnetwork_node", 1, 100_000),
        ("announce_fetch_limit_lxmf_propagation", 1, 100_000),
        ("announce_fetch_limit_map_data", 1, 100_000),
        ("announce_search_max_fetch", 100, 10_000),
        ("discovered_interfaces_max_return", 1, 50_000),
    ]
    for key, lo, hi in _announce_int_fields:
        if key not in data:
            continue
        val = data[key]
        if val is None or val == "":
            getattr(app.config, key).set(None)
            continue
        try:
            v = int(val)
            v = max(lo, min(hi, v))
            getattr(app.config, key).set(v)
        except (TypeError, ValueError):
            getattr(app.config, key).set(None)

    if "lxmf_preferred_propagation_node_destination_hash" in data:
        # update config value
        value = data["lxmf_preferred_propagation_node_destination_hash"]
        app.config.lxmf_preferred_propagation_node_destination_hash.set(value)

        # update active propagation node
        app.set_active_propagation_node(value)

    if "lxmf_preferred_propagation_node_auto_select" in data:
        value = app._parse_bool(
            data["lxmf_preferred_propagation_node_auto_select"],
        )
        app.config.lxmf_preferred_propagation_node_auto_select.set(value)

    # update inbound stamp cost (for direct delivery messages)
    if "lxmf_inbound_stamp_cost" in data:
        value = app._coerce_int(data["lxmf_inbound_stamp_cost"])
        if value is None:
            value = app.config.lxmf_inbound_stamp_cost.get()
        # 0 disables inbound stamps, and otherwise clamp to 1-254 (LXMF/LXMRouter)
        if value < 0:
            value = 0
        elif value >= 255:
            value = 254
        # If block strangers is active, store the desired value for later restore
        # but keep the enforced max cost active
        if app.config.block_all_from_strangers.get():
            app.config.lxmf_inbound_stamp_cost_before_block.set(value)
        else:
            app.config.lxmf_inbound_stamp_cost.set(value)
            # update the inbound stamp cost on the delivery destination
            app.message_router.set_inbound_stamp_cost(
                app.local_lxmf_destination.hash,
                value,
            )
            if value > 0:
                app.message_router.enforce_stamps()
            elif hasattr(app.message_router, "ignore_stamps"):
                app.message_router.ignore_stamps()
            # re-announce to update the stamp cost in announces
            app.local_lxmf_destination.display_name = app.config.display_name.get()
            app.message_router.announce(
                destination_hash=app.local_lxmf_destination.hash,
            )

    # update propagation node stamp cost (for messages propagated through your node)
    if "lxmf_propagation_node_stamp_cost" in data:
        value = app._coerce_int(data["lxmf_propagation_node_stamp_cost"])
        if value is None:
            value = app.config.lxmf_propagation_node_stamp_cost.get()
        # validate stamp cost (must be at least 13, per LXMF minimum)
        if value < 13:
            value = 13
        elif value >= 255:
            value = 254
        app.config.lxmf_propagation_node_stamp_cost.set(value)
        # update the propagation stamp cost on the router
        app.message_router.propagation_stamp_cost = value
        # re-announce propagation node if enabled
        if app.config.lxmf_local_propagation_node_enabled.get():
            app.message_router.announce_propagation_node()

    if "lxmf_propagation_sequential_validation" in data:
        value = app._parse_bool(
            data["lxmf_propagation_sequential_validation"],
        )
        app.config.lxmf_propagation_sequential_validation.set(value)
        if app.message_router is not None:
            app.message_router.propagation_sequential_validation = value

    if "lxmf_propagation_static_peers_bypass_sequential" in data:
        value = app._parse_bool(
            data["lxmf_propagation_static_peers_bypass_sequential"],
        )
        app.config.lxmf_propagation_static_peers_bypass_sequential.set(value)
        if app.message_router is not None:
            app.message_router.propagation_static_peer_sequential = not value

    if "lxmf_propagation_max_inbound_syncs" in data:
        value = app._coerce_int(data["lxmf_propagation_max_inbound_syncs"])
        if value is None:
            value = app.config.lxmf_propagation_max_inbound_syncs.get()
        if value < 1:
            value = 1
        elif value > 64:
            value = 64
        app.config.lxmf_propagation_max_inbound_syncs.set(value)
        if app.message_router is not None:
            app.message_router.propagation_max_inbound_syncs = value

    # update auto sync interval
    if "lxmf_preferred_propagation_node_auto_sync_interval_seconds" in data:
        value = app._coerce_int(
            data["lxmf_preferred_propagation_node_auto_sync_interval_seconds"],
        )
        if value is None:
            value = app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
        app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.set(
            value,
        )

    if "lxmf_local_propagation_node_enabled" in data:
        # update config value
        value = app._parse_bool(data["lxmf_local_propagation_node_enabled"])
        app.config.lxmf_local_propagation_node_enabled.set(value)

        # enable or disable local propagation node
        app.enable_local_propagation_node(value)

    # update lxmf user icon name in config
    if "lxmf_user_icon_name" in data:
        app.config.lxmf_user_icon_name.set(data["lxmf_user_icon_name"])
        app.database.misc.clear_last_sent_icon_hashes()
        app.update_identity_metadata_cache()

    # update lxmf user icon foreground colour in config
    if "lxmf_user_icon_foreground_colour" in data:
        app.config.lxmf_user_icon_foreground_colour.set(
            data["lxmf_user_icon_foreground_colour"],
        )
        app.database.misc.clear_last_sent_icon_hashes()
        app.update_identity_metadata_cache()

    # update lxmf user icon background colour in config
    if "lxmf_user_icon_background_colour" in data:
        app.config.lxmf_user_icon_background_colour.set(
            data["lxmf_user_icon_background_colour"],
        )
        app.database.misc.clear_last_sent_icon_hashes()
        app.update_identity_metadata_cache()

    # update archiver settings
    if "page_archiver_enabled" in data:
        app.config.page_archiver_enabled.set(
            app._parse_bool(data["page_archiver_enabled"]),
        )

    if "page_archiver_max_versions" in data:
        value = app._coerce_int(data["page_archiver_max_versions"])
        if value is not None:
            app.config.page_archiver_max_versions.set(value)

    if "archives_max_storage_gb" in data:
        value = app._coerce_int(data["archives_max_storage_gb"])
        if value is not None:
            app.config.archives_max_storage_gb.set(value)

    if "backup_max_count" in data:
        try:
            value = int(data["backup_max_count"])
        except (TypeError, ValueError):
            value = app.config.backup_max_count.default_value
        value = max(1, min(value, 50))
        app.config.backup_max_count.set(value)

    # update crawler settings
    if "crawler_enabled" in data:
        app.config.crawler_enabled.set(app._parse_bool(data["crawler_enabled"]))

    if "crawler_max_retries" in data:
        try:
            value = int(data["crawler_max_retries"])
        except (TypeError, ValueError):
            value = app.config.crawler_max_retries.default_value
        app.config.crawler_max_retries.set(value)

    if "crawler_retry_delay_seconds" in data:
        try:
            value = int(data["crawler_retry_delay_seconds"])
        except (TypeError, ValueError):
            value = app.config.crawler_retry_delay_seconds.default_value
        app.config.crawler_retry_delay_seconds.set(value)

    if "crawler_max_concurrent" in data:
        try:
            value = int(data["crawler_max_concurrent"])
        except (TypeError, ValueError):
            value = app.config.crawler_max_concurrent.default_value
        app.config.crawler_max_concurrent.set(value)

    if "crawler_max_hops" in data:
        try:
            value = int(data["crawler_max_hops"])
        except (TypeError, ValueError):
            value = app.config.crawler_max_hops.default_value
        app.config.crawler_max_hops.set(max(1, min(16, value)))

    if "crawler_max_rtt_ms" in data:
        try:
            value = int(data["crawler_max_rtt_ms"])
        except (TypeError, ValueError):
            value = app.config.crawler_max_rtt_ms.default_value
        app.config.crawler_max_rtt_ms.set(max(100, min(60000, value)))

    if "crawler_max_depth" in data:
        try:
            value = int(data["crawler_max_depth"])
        except (TypeError, ValueError):
            value = app.config.crawler_max_depth.default_value
        app.config.crawler_max_depth.set(max(0, min(2, value)))

    if "crawler_max_pages_per_node" in data:
        try:
            value = int(data["crawler_max_pages_per_node"])
        except (TypeError, ValueError):
            value = app.config.crawler_max_pages_per_node.default_value
        app.config.crawler_max_pages_per_node.set(max(1, min(20, value)))

    if "crawler_requests_per_day_per_node" in data:
        try:
            value = int(data["crawler_requests_per_day_per_node"])
        except (TypeError, ValueError):
            value = app.config.crawler_requests_per_day_per_node.default_value
        app.config.crawler_requests_per_day_per_node.set(max(1, min(3, value)))

    if "crawler_refresh_days" in data:
        try:
            value = int(data["crawler_refresh_days"])
        except (TypeError, ValueError):
            value = app.config.crawler_refresh_days.default_value
        app.config.crawler_refresh_days.set(max(1, min(365, value)))

    if "auth_enabled" in data:
        value = app._parse_bool(data["auth_enabled"])
        app.config.auth_enabled.set(value)

        # if disabling auth, also remove the password hash from config
        if not value:
            app.config.auth_password_hash.set(None)

    if "privacy_mode_enabled" in data:
        app.config.privacy_mode_enabled.set(
            app._parse_bool(data["privacy_mode_enabled"]),
        )

    if "multi_session_warning_enabled" in data:
        app.config.multi_session_warning_enabled.set(
            app._parse_bool(data["multi_session_warning_enabled"]),
        )

    # update map settings
    if "map_offline_enabled" in data:
        app.config.map_offline_enabled.set(
            app._parse_bool(data["map_offline_enabled"]),
        )

    if "map_default_lat" in data:
        app.config.map_default_lat.set(str(data["map_default_lat"]))

    if "map_default_lon" in data:
        app.config.map_default_lon.set(str(data["map_default_lon"]))

    if "map_default_zoom" in data:
        try:
            value = int(data["map_default_zoom"])
        except (TypeError, ValueError):
            value = None
        if value is not None:
            app.config.map_default_zoom.set(value)

    if "map_mbtiles_dir" in data:
        app.config.map_mbtiles_dir.set(data["map_mbtiles_dir"])

    if "map_tile_cache_enabled" in data:
        app.config.map_tile_cache_enabled.set(
            app._parse_bool(data["map_tile_cache_enabled"]),
        )

    if "map_tile_server_url" in data:
        app.config.map_tile_server_url.set(data["map_tile_server_url"])

    if "map_nominatim_api_url" in data:
        app.config.map_nominatim_api_url.set(data["map_nominatim_api_url"])

    for overlay_key in CONFIG_CLAMPS:
        if overlay_key in data:
            try:
                value = int(data[overlay_key])
            except (TypeError, ValueError):
                continue
            getattr(app.config, overlay_key).set(
                clamp_overlay_config_value(overlay_key, value),
            )

    # update location settings
    if "location_source" in data:
        app.config.location_source.set(data["location_source"])

    if "location_manual_lat" in data:
        app.config.location_manual_lat.set(str(data["location_manual_lat"]))

    if "location_manual_lon" in data:
        app.config.location_manual_lon.set(str(data["location_manual_lon"]))

    if "location_manual_alt" in data:
        app.config.location_manual_alt.set(str(data["location_manual_alt"]))

    if "telemetry_enabled" in data:
        app.config.telemetry_enabled.set(
            app._parse_bool(data["telemetry_enabled"]),
        )

    if "nomad_render_markdown_enabled" in data:
        app.config.nomad_render_markdown_enabled.set(
            app._parse_bool(data["nomad_render_markdown_enabled"]),
        )

    if "nomad_render_html_enabled" in data:
        app.config.nomad_render_html_enabled.set(
            app._parse_bool(data["nomad_render_html_enabled"]),
        )

    if "nomad_render_plaintext_enabled" in data:
        app.config.nomad_render_plaintext_enabled.set(
            app._parse_bool(data["nomad_render_plaintext_enabled"]),
        )

    if "nomad_micron_wasm_enabled" in data:
        app.config.nomad_micron_wasm_enabled.set(
            app._parse_bool(data["nomad_micron_wasm_enabled"]),
        )
        if not app.config.nomad_micron_wasm_enabled.get():
            app.config.nomad_micron_default_engine.set("js")

    if "nomad_micron_default_engine" in data:
        if app.config.nomad_micron_wasm_enabled.get():
            raw = str(data["nomad_micron_default_engine"] or "").strip().lower()
            app.config.nomad_micron_default_engine.set(
                "wasm" if raw == "wasm" else "js",
            )

    if "nomad_default_page_path" in data:
        from meshchatx.src.backend.page_node import is_allowed_page_filename

        raw = data["nomad_default_page_path"]
        if raw is None or str(raw).strip() == "":
            app.config.nomad_default_page_path.set("/page/index.mu")
        else:
            s = str(raw).strip()
            if s.startswith("/page/"):
                base = s[6:]
                if (
                    base
                    and "/" not in base
                    and ".." not in base
                    and is_allowed_page_filename(base)
                ):
                    app.config.nomad_default_page_path.set(s)

    if "local_message_auto_delete_enabled" in data:
        app.config.local_message_auto_delete_enabled.set(
            app._parse_bool(data["local_message_auto_delete_enabled"]),
        )
    if "message_blocklist_enabled" in data:
        app.config.message_blocklist_enabled.set(
            app._parse_bool(data["message_blocklist_enabled"]),
        )
    if (
        "local_message_auto_delete_value" in data
        or "local_message_auto_delete_unit" in data
    ):
        from meshchatx.src.backend.local_message_retention import (
            MAX_VALUE_DAYS,
            MAX_VALUE_MONTHS,
            normalize_unit,
        )

        u_str = str(
            data.get("local_message_auto_delete_unit")
            or app.config.local_message_auto_delete_unit.get()
            or "days",
        )
        u_norm = normalize_unit(u_str)
        if "local_message_auto_delete_unit" in data:
            app.config.local_message_auto_delete_unit.set(u_norm)
        v_raw = data.get(
            "local_message_auto_delete_value",
            app.config.local_message_auto_delete_value.get(),
        )
        try:
            v = int(v_raw)
        except (TypeError, ValueError):
            v = 30
        v = max(1, v)
        v = min(v, MAX_VALUE_MONTHS if u_norm == "months" else MAX_VALUE_DAYS)
        app.config.local_message_auto_delete_value.set(v)

    if "block_attachments_from_strangers" in data:
        app.config.block_attachments_from_strangers.set(
            app._parse_bool(data["block_attachments_from_strangers"]),
        )

    if "block_all_from_strangers" in data:
        new_value = app._parse_bool(data["block_all_from_strangers"])
        old_value = app.config.block_all_from_strangers.get()
        app.config.block_all_from_strangers.set(new_value)
        if new_value and not old_value:
            # Enabling block strangers: save current stamp cost and set to max
            current_cost = app.config.lxmf_inbound_stamp_cost.get()
            if not isinstance(current_cost, int):
                current_cost = 0
            if current_cost < 0:
                current_cost = 0
            elif current_cost > 254:
                current_cost = 254
            app.config.lxmf_inbound_stamp_cost_before_block.set(current_cost)
            app.config.lxmf_inbound_stamp_cost.set(254)
            if app.message_router and app.local_lxmf_destination:
                app.message_router.set_inbound_stamp_cost(
                    app.local_lxmf_destination.hash,
                    254,
                )
                app.message_router.enforce_stamps()
                app.local_lxmf_destination.display_name = app.config.display_name.get()
                app.message_router.announce(
                    destination_hash=app.local_lxmf_destination.hash,
                )
        elif not new_value and old_value:
            # Disabling block strangers: restore previous stamp cost.
            # Zero is a valid prior cost (stamps off). Only fall back to 8
            # when no prior cost was saved (sentinel outside 0..254).
            saved = app.config.lxmf_inbound_stamp_cost_before_block.get()
            if isinstance(saved, int) and 0 <= saved <= 254:
                restore_cost = saved
            else:
                restore_cost = 8
            app.config.lxmf_inbound_stamp_cost.set(restore_cost)
            app.config.lxmf_inbound_stamp_cost_before_block.set(-1)
            if app.message_router and app.local_lxmf_destination:
                app.message_router.set_inbound_stamp_cost(
                    app.local_lxmf_destination.hash,
                    restore_cost,
                )
                if restore_cost > 0:
                    app.message_router.enforce_stamps()
                elif hasattr(app.message_router, "ignore_stamps"):
                    app.message_router.ignore_stamps()
                app.local_lxmf_destination.display_name = app.config.display_name.get()
                app.message_router.announce(
                    destination_hash=app.local_lxmf_destination.hash,
                )
        app.sync_telephone_call_policy()

    # update flood protection settings
    if "lxmf_flood_protection_enabled" in data:
        app.config.lxmf_flood_protection_enabled.set(
            app._parse_bool(data["lxmf_flood_protection_enabled"]),
        )
    if "lxmf_flood_threshold_per_minute" in data:
        try:
            value = int(data["lxmf_flood_threshold_per_minute"])
            value = max(1, min(value, 1000))
            app.config.lxmf_flood_threshold_per_minute.set(value)
        except (TypeError, ValueError):
            pass
    if "lxmf_flood_max_stamp_cost" in data:
        try:
            value = int(data["lxmf_flood_max_stamp_cost"])
            value = max(1, min(value, 254))
            app.config.lxmf_flood_max_stamp_cost.set(value)
        except (TypeError, ValueError):
            pass
    if "lxmf_flood_cooldown_seconds" in data:
        try:
            value = int(data["lxmf_flood_cooldown_seconds"])
            value = max(30, min(value, 3600))
            app.config.lxmf_flood_cooldown_seconds.set(value)
        except (TypeError, ValueError):
            pass

    if "show_unknown_contact_banner" in data:
        app.config.show_unknown_contact_banner.set(
            app._parse_bool(data["show_unknown_contact_banner"]),
        )

    if "warn_on_stranger_links" in data:
        app.config.warn_on_stranger_links.set(
            app._parse_bool(data["warn_on_stranger_links"]),
        )

    # update banishment settings
    if "banished_effect_enabled" in data:
        app.config.banished_effect_enabled.set(
            app._parse_bool(data["banished_effect_enabled"]),
        )

    if "banished_text" in data:
        app.config.banished_text.set(data["banished_text"])

    if "banished_color" in data:
        app.config.banished_color.set(data["banished_color"])

    if "message_font_size" in data:
        try:
            value = int(data["message_font_size"])
        except (TypeError, ValueError):
            value = None
        if value is not None:
            app.config.message_font_size.set(value)

    if "messages_sidebar_position" in data:
        raw = data["messages_sidebar_position"]
        if raw is not None:
            s = str(raw).strip().lower()
            if s in ("left", "right"):
                app.config.messages_sidebar_position.set(s)

    if "app_sidebar_layout" in data:
        raw = data["app_sidebar_layout"]
        if raw is not None:
            s = str(raw).strip().lower()
            if s in ("grouped", "classic"):
                app.config.app_sidebar_layout.set(s)

    if "message_icon_size" in data:
        try:
            value = int(data["message_icon_size"])
        except (TypeError, ValueError):
            value = None
        if value is not None:
            value = max(12, min(value, 96))
            app.config.message_icon_size.set(value)

    if "ui_transparency" in data:
        try:
            value = int(data["ui_transparency"])
        except (TypeError, ValueError):
            value = None
        if value is not None:
            app.config.ui_transparency.set(max(0, min(value, 100)))

    if "ui_glass_enabled" in data:
        app.config.ui_glass_enabled.set(
            app._parse_bool(data["ui_glass_enabled"]),
        )

    if "live_transport_mode" in data:
        mode = str(data["live_transport_mode"] or "auto").strip().lower()
        if mode not in ("auto", "websocket", "webtransport"):
            mode = "auto"
        app.config.live_transport_mode.set(mode)

    if "webtransport_sidecar_enabled" in data:
        app.config.webtransport_sidecar_enabled.set(
            app._parse_bool(data["webtransport_sidecar_enabled"]),
        )
        try:
            from meshchatx.src.backend.webtransport_sidecar import (
                try_start_webtransport_sidecar,
            )

            AsyncUtils.run_async(try_start_webtransport_sidecar(app))
        except Exception:
            pass

    if "messages_multi_pane_enabled" in data:
        app.config.messages_multi_pane_enabled.set(
            app._parse_bool(data["messages_multi_pane_enabled"]),
        )

    if "nomad_tabs_enabled" in data:
        app.config.nomad_tabs_enabled.set(
            app._parse_bool(data["nomad_tabs_enabled"]),
        )
    if "rrc_enabled" in data:
        app.config.rrc_enabled.set(app._parse_bool(data["rrc_enabled"]))
    if "rrc_unread_badges_enabled" in data:
        app.config.rrc_unread_badges_enabled.set(
            app._parse_bool(data["rrc_unread_badges_enabled"]),
        )

    if "message_outbound_bubble_color" in data:
        app.config.message_outbound_bubble_color.set(
            data["message_outbound_bubble_color"],
        )

    if "message_inbound_bubble_color" in data:
        app.config.message_inbound_bubble_color.set(
            data["message_inbound_bubble_color"],
        )

    if "message_failed_bubble_color" in data:
        app.config.message_failed_bubble_color.set(
            data["message_failed_bubble_color"],
        )

    if "message_waiting_bubble_color" in data:
        app.config.message_waiting_bubble_color.set(
            data["message_waiting_bubble_color"],
        )

    # update desktop settings
    if "desktop_open_calls_in_separate_window" in data:
        app.config.desktop_open_calls_in_separate_window.set(
            app._parse_bool(data["desktop_open_calls_in_separate_window"]),
        )

    if "desktop_hardware_acceleration_enabled" in data:
        enabled = app._parse_bool(data["desktop_hardware_acceleration_enabled"])
        app.config.desktop_hardware_acceleration_enabled.set(enabled)

        # write flag for electron to read on next launch
        try:
            disable_gpu_file = os.path.join(app.storage_dir, "disable-gpu")
            if not enabled:
                with open(disable_gpu_file, "w") as f:
                    f.write("true")
            elif os.path.exists(disable_gpu_file):
                os.remove(disable_gpu_file)
        except Exception as e:
            print(f"Failed to update GPU disable flag: {e}")

    if "blackhole_integration_enabled" in data:
        value = app._parse_bool(data["blackhole_integration_enabled"])
        app.config.blackhole_integration_enabled.set(value)

    for _k in (
        "announce_store_lxmf_delivery",
        "announce_store_lxst_telephony",
        "announce_store_nomadnetwork_node",
        "announce_store_lxmf_propagation",
        "announce_store_map_data",
    ):
        if _k in data:
            getattr(app.config, _k).set(app._parse_bool(data[_k]))

    # update csp extra sources
    if "csp_extra_connect_src" in data:
        app.config.csp_extra_connect_src.set(data["csp_extra_connect_src"])
    if "csp_extra_img_src" in data:
        app.config.csp_extra_img_src.set(data["csp_extra_img_src"])
    if "csp_extra_frame_src" in data:
        app.config.csp_extra_frame_src.set(data["csp_extra_frame_src"])
    if "csp_extra_script_src" in data:
        app.config.csp_extra_script_src.set(data["csp_extra_script_src"])
    if "csp_extra_style_src" in data:
        app.config.csp_extra_style_src.set(data["csp_extra_style_src"])

    # update voicemail settings
    if "voicemail_enabled" in data:
        app.config.voicemail_enabled.set(
            app._parse_bool(data["voicemail_enabled"]),
        )

    if "voicemail_greeting" in data:
        app.config.voicemail_greeting.set(data["voicemail_greeting"])

    if "voicemail_auto_answer_delay_seconds" in data:
        value = app._coerce_int(data["voicemail_auto_answer_delay_seconds"])
        if value is not None:
            app.config.voicemail_auto_answer_delay_seconds.set(value)

    if "voicemail_max_recording_seconds" in data:
        value = app._coerce_int(data["voicemail_max_recording_seconds"])
        if value is not None:
            app.config.voicemail_max_recording_seconds.set(value)

    if "voicemail_tts_speed" in data:
        value = app._coerce_int(data["voicemail_tts_speed"])
        if value is not None:
            app.config.voicemail_tts_speed.set(value)

    if "voicemail_tts_pitch" in data:
        value = app._coerce_int(data["voicemail_tts_pitch"])
        if value is not None:
            app.config.voicemail_tts_pitch.set(value)

    if "voicemail_tts_voice" in data:
        app.config.voicemail_tts_voice.set(data["voicemail_tts_voice"])

    if "voicemail_tts_word_gap" in data:
        value = app._coerce_int(data["voicemail_tts_word_gap"])
        if value is not None:
            app.config.voicemail_tts_word_gap.set(value)

    # update ringtone settings
    if "custom_ringtone_enabled" in data:
        app.config.custom_ringtone_enabled.set(
            app._parse_bool(data["custom_ringtone_enabled"]),
        )
    if "ringtone_preferred_id" in data:
        value = app._coerce_int(data["ringtone_preferred_id"])
        if value is not None:
            app.config.ringtone_preferred_id.set(value)
    if "ringtone_volume" in data:
        value = app._coerce_int(data["ringtone_volume"])
        if value is not None:
            app.config.ringtone_volume.set(value)

    if "notification_sound_enabled" in data:
        app.config.notification_sound_enabled.set(
            app._parse_bool(data["notification_sound_enabled"]),
        )
    if "notification_sound_preferred_id" in data:
        value = app._coerce_int(data["notification_sound_preferred_id"])
        if value is not None:
            app.config.notification_sound_preferred_id.set(value)
    if "notification_sound_volume" in data:
        value = app._coerce_int(data["notification_sound_volume"])
        if value is not None:
            app.config.notification_sound_volume.set(value)

    if "do_not_disturb_enabled" in data:
        app.config.do_not_disturb_enabled.set(
            app._parse_bool(data["do_not_disturb_enabled"]),
        )
        app.sync_telephone_call_policy()

    if "telephone_enabled" in data:
        value = app._parse_bool(data["telephone_enabled"])
        app.config.telephone_enabled.set(value)
        if not value and app.telephone_manager and app.telephone_manager.telephone:
            app.telephone_manager.teardown()
        elif value and app.telephone_manager:
            app.telephone_manager.init_telephone()
            app.sync_telephone_call_policy()

    if "telephone_allow_calls_from_contacts_only" in data:
        app.config.telephone_allow_calls_from_contacts_only.set(
            app._parse_bool(data["telephone_allow_calls_from_contacts_only"]),
        )
        app.sync_telephone_call_policy()

    if "telephone_announce_enabled" in data:
        app.config.telephone_announce_enabled.set(
            app._parse_bool(data["telephone_announce_enabled"]),
        )

    if "call_recording_enabled" in data:
        value = app._parse_bool(data["call_recording_enabled"])
        app.config.call_recording_enabled.set(value)
        # if a call is active, start or stop recording immediately
        if (
            app.telephone_manager
            and app.telephone_manager.telephone
            and app.telephone_manager.telephone.active_call
        ):
            if value:
                app.telephone_manager.start_recording()
            else:
                app.telephone_manager.stop_recording()

    if "telephone_tone_generator_enabled" in data:
        app.config.telephone_tone_generator_enabled.set(
            app._parse_bool(data["telephone_tone_generator_enabled"]),
        )

    if "telephone_tone_generator_volume" in data:
        value = app._coerce_int(data["telephone_tone_generator_volume"])
        if value is not None:
            app.config.telephone_tone_generator_volume.set(value)

    if "telephone_audio_profile_id" in data:
        profile_id = app._coerce_int(data["telephone_audio_profile_id"])
        if profile_id is None:
            profile_id = app.config.telephone_audio_profile_id.get()
        app.config.telephone_audio_profile_id.set(profile_id)
        if app.telephone_manager:
            await asyncio.to_thread(
                app.telephone_manager.apply_preferred_profile,
                profile_id,
            )

    if "telephone_call_mode_id" in data:
        mode_id = app._coerce_int(data["telephone_call_mode_id"])
        if mode_id is None:
            mode_id = app.config.telephone_call_mode_id.get()
        app.config.telephone_call_mode_id.set(mode_id)
        if app.telephone_manager:
            await asyncio.to_thread(
                app.telephone_manager.apply_preferred_mode,
                mode_id,
            )

    if "telephone_web_audio_enabled" in data:
        app.config.telephone_web_audio_enabled.set(
            app._parse_bool(data["telephone_web_audio_enabled"]),
        )

    if "telephone_web_audio_allow_fallback" in data:
        app.config.telephone_web_audio_allow_fallback.set(
            app._parse_bool(data["telephone_web_audio_allow_fallback"]),
        )

    if "translator_argos_enabled" in data:
        v = app._parse_bool(data["translator_argos_enabled"])
        app.config.translator_argos_enabled.set(v)
        if hasattr(app, "translator_handler"):
            app.translator_handler.translator_argos_enabled = v

    if "translator_libretranslate_enabled" in data:
        v = app._parse_bool(data["translator_libretranslate_enabled"])
        app.config.translator_libretranslate_enabled.set(v)
        if hasattr(app, "translator_handler"):
            app.translator_handler.translator_libretranslate_enabled = v

    if "translator_enabled" in data:
        v = app._parse_bool(data["translator_enabled"])
        app.config.translator_argos_enabled.set(v)
        app.config.translator_libretranslate_enabled.set(v)
        if hasattr(app, "translator_handler"):
            th = app.translator_handler
            th.translator_argos_enabled = v
            th.translator_libretranslate_enabled = v

    if "libretranslate_url" in data:
        value = data["libretranslate_url"]
        app.config.libretranslate_url.set(value)
        if hasattr(app, "translator_handler"):
            app.translator_handler.libretranslate_url = value

    if "libretranslate_api_key" in data:
        from meshchatx.src.backend.translator_handler import (
            _normalize_optional_libretranslate_api_key,
        )

        raw = data["libretranslate_api_key"]
        if raw is None or raw == "":
            norm = None
        else:
            norm = _normalize_optional_libretranslate_api_key(str(raw))

        app.config.libretranslate_api_key.set(norm)
        if hasattr(app, "translator_handler"):
            app.translator_handler.libretranslate_api_key = norm

    # send config to websocket clients
    await app.send_config_to_websocket_clients()
    if "multi_session_warning_enabled" in data:
        await app.send_active_sessions_to_websocket_clients()


# converts nomadnetwork page variables from a string to a map
# converts: "field1=123|field2=456"
# to the following map:
# - var_field1: 123
# - var_field2: 456
