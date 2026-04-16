# SPDX-License-Identifier: 0BSD


class ConfigManager:
    def __init__(self, db):
        self.db = db

        # all possible config items
        self.database_version = self.IntConfig(self, "database_version", None)
        self.display_name = self.StringConfig(self, "display_name", "Anonymous Peer")
        self.auto_announce_enabled = self.BoolConfig(
            self,
            "auto_announce_enabled",
            False,
        )
        self.auto_announce_interval_seconds = self.IntConfig(
            self,
            "auto_announce_interval_seconds",
            0,
        )
        self.last_announced_at = self.IntConfig(self, "last_announced_at", None)
        self.theme = self.StringConfig(self, "theme", "light")
        self.language = self.StringConfig(self, "language", "en")
        self.auto_resend_failed_messages_when_announce_received = self.BoolConfig(
            self,
            "auto_resend_failed_messages_when_announce_received",
            True,
        )
        self.allow_auto_resending_failed_messages_with_attachments = self.BoolConfig(
            self,
            "allow_auto_resending_failed_messages_with_attachments",
            False,
        )
        self.auto_send_failed_messages_to_propagation_node = self.BoolConfig(
            self,
            "auto_send_failed_messages_to_propagation_node",
            False,
        )
        self.show_suggested_community_interfaces = self.BoolConfig(
            self,
            "show_suggested_community_interfaces",
            True,
        )
        self.lxmf_delivery_transfer_limit_in_bytes = self.IntConfig(
            self,
            "lxmf_delivery_transfer_limit_in_bytes",
            1000 * 1000 * 10,
        )  # 10MB
        self.lxmf_propagation_transfer_limit_in_bytes = self.IntConfig(
            self,
            "lxmf_propagation_transfer_limit_in_bytes",
            1000 * 256,
        )  # 256KB (LXMF default)
        self.lxmf_propagation_sync_limit_in_bytes = self.IntConfig(
            self,
            "lxmf_propagation_sync_limit_in_bytes",
            1000 * 10240,
        )  # 10MB (LXMF default)
        self.lxmf_preferred_propagation_node_destination_hash = self.StringConfig(
            self,
            "lxmf_preferred_propagation_node_destination_hash",
            None,
        )
        self.lxmf_preferred_propagation_node_auto_select = self.BoolConfig(
            self,
            "lxmf_preferred_propagation_node_auto_select",
            False,
        )
        self.lxmf_preferred_propagation_node_auto_sync_interval_seconds = (
            self.IntConfig(
                self,
                "lxmf_preferred_propagation_node_auto_sync_interval_seconds",
                0,
            )
        )
        self.lxmf_preferred_propagation_node_last_synced_at = self.IntConfig(
            self,
            "lxmf_preferred_propagation_node_last_synced_at",
            None,
        )
        self.lxmf_address_hash = self.StringConfig(self, "lxmf_address_hash", None)
        self.lxst_address_hash = self.StringConfig(self, "lxst_address_hash", None)
        self.lxmf_local_propagation_node_enabled = self.BoolConfig(
            self,
            "lxmf_local_propagation_node_enabled",
            False,
        )
        self.lxmf_user_icon_name = self.StringConfig(self, "lxmf_user_icon_name", None)
        self.lxmf_user_icon_foreground_colour = self.StringConfig(
            self,
            "lxmf_user_icon_foreground_colour",
            None,
        )
        self.lxmf_user_icon_background_colour = self.StringConfig(
            self,
            "lxmf_user_icon_background_colour",
            None,
        )
        self.lxmf_inbound_stamp_cost = self.IntConfig(
            self,
            "lxmf_inbound_stamp_cost",
            8,
        )  # for direct delivery messages
        self.lxmf_propagation_node_stamp_cost = self.IntConfig(
            self,
            "lxmf_propagation_node_stamp_cost",
            16,
        )  # for propagation node messages
        self.page_archiver_enabled = self.BoolConfig(
            self,
            "page_archiver_enabled",
            True,
        )
        self.page_archiver_max_versions = self.IntConfig(
            self,
            "page_archiver_max_versions",
            5,
        )
        self.archives_max_storage_gb = self.IntConfig(
            self,
            "archives_max_storage_gb",
            1,
        )
        self.backup_max_count = self.IntConfig(self, "backup_max_count", 5)
        self.crawler_enabled = self.BoolConfig(self, "crawler_enabled", False)
        self.crawler_max_retries = self.IntConfig(self, "crawler_max_retries", 3)
        self.crawler_retry_delay_seconds = self.IntConfig(
            self,
            "crawler_retry_delay_seconds",
            3600,
        )
        self.crawler_max_concurrent = self.IntConfig(self, "crawler_max_concurrent", 1)
        self.auth_enabled = self.BoolConfig(self, "auth_enabled", False)
        self.auth_password_hash = self.StringConfig(self, "auth_password_hash", None)
        self.auth_session_secret = self.StringConfig(self, "auth_session_secret", None)
        self.docs_downloaded = self.BoolConfig(self, "docs_downloaded", False)
        self.initial_docs_download_attempted = self.BoolConfig(
            self,
            "initial_docs_download_attempted",
            False,
        )
        self.gitea_base_url = self.StringConfig(
            self,
            "gitea_base_url",
            "https://git.quad4.io",
        )
        self.docs_download_urls = self.StringConfig(
            self,
            "docs_download_urls",
            "https://git.quad4.io/Reticulum/reticulum_website/archive/main.zip,https://github.com/markqvist/reticulum_website/archive/refs/heads/main.zip",
        )

        # desktop config
        self.desktop_open_calls_in_separate_window = self.BoolConfig(
            self,
            "desktop_open_calls_in_separate_window",
            False,
        )
        self.desktop_hardware_acceleration_enabled = self.BoolConfig(
            self,
            "desktop_hardware_acceleration_enabled",
            True,
        )

        # voicemail config
        self.voicemail_enabled = self.BoolConfig(self, "voicemail_enabled", False)
        self.voicemail_greeting = self.StringConfig(
            self,
            "voicemail_greeting",
            "Hello, I am not available right now. Please leave a message after the beep.",
        )
        self.voicemail_auto_answer_delay_seconds = self.IntConfig(
            self,
            "voicemail_auto_answer_delay_seconds",
            20,
        )
        self.voicemail_max_recording_seconds = self.IntConfig(
            self,
            "voicemail_max_recording_seconds",
            60,
        )
        self.voicemail_tts_speed = self.IntConfig(self, "voicemail_tts_speed", 130)
        self.voicemail_tts_pitch = self.IntConfig(self, "voicemail_tts_pitch", 45)
        self.voicemail_tts_voice = self.StringConfig(
            self,
            "voicemail_tts_voice",
            "en-us+f3",
        )
        self.voicemail_tts_word_gap = self.IntConfig(self, "voicemail_tts_word_gap", 5)

        # ringtone config
        self.custom_ringtone_enabled = self.BoolConfig(
            self,
            "custom_ringtone_enabled",
            False,
        )
        self.ringtone_filename = self.StringConfig(self, "ringtone_filename", None)
        self.ringtone_preferred_id = self.IntConfig(self, "ringtone_preferred_id", 0)
        self.ringtone_volume = self.IntConfig(self, "ringtone_volume", 100)

        # telephony config
        self.do_not_disturb_enabled = self.BoolConfig(
            self,
            "do_not_disturb_enabled",
            False,
        )
        self.telephone_allow_calls_from_contacts_only = self.BoolConfig(
            self,
            "telephone_allow_calls_from_contacts_only",
            False,
        )
        self.telephone_audio_profile_id = self.IntConfig(
            self,
            "telephone_audio_profile_id",
            2,  # Default to Voice (profile 2)
        )
        self.telephone_web_audio_enabled = self.BoolConfig(
            self,
            "telephone_web_audio_enabled",
            False,
        )
        self.telephone_web_audio_allow_fallback = self.BoolConfig(
            self,
            "telephone_web_audio_allow_fallback",
            True,
        )
        self.call_recording_enabled = self.BoolConfig(
            self,
            "call_recording_enabled",
            False,
        )
        self.telephone_tone_generator_enabled = self.BoolConfig(
            self,
            "telephone_tone_generator_enabled",
            True,
        )
        self.telephone_tone_generator_volume = self.IntConfig(
            self,
            "telephone_tone_generator_volume",
            50,
        )

        # map config
        self.map_offline_enabled = self.BoolConfig(self, "map_offline_enabled", False)
        self.map_offline_path = self.StringConfig(self, "map_offline_path", None)
        self.map_mbtiles_dir = self.StringConfig(self, "map_mbtiles_dir", None)
        self.map_tile_cache_enabled = self.BoolConfig(
            self,
            "map_tile_cache_enabled",
            True,
        )
        self.map_default_lat = self.StringConfig(self, "map_default_lat", "0.0")
        self.map_default_lon = self.StringConfig(self, "map_default_lon", "0.0")
        self.map_default_zoom = self.IntConfig(self, "map_default_zoom", 2)
        self.map_tile_server_url = self.StringConfig(
            self,
            "map_tile_server_url",
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        )
        self.map_nominatim_api_url = self.StringConfig(
            self,
            "map_nominatim_api_url",
            "https://nominatim.openstreetmap.org",
        )

        # telemetry config
        self.telemetry_enabled = self.BoolConfig(self, "telemetry_enabled", False)

        # translator config
        self.translator_enabled = self.BoolConfig(self, "translator_enabled", False)
        self.libretranslate_url = self.StringConfig(
            self,
            "libretranslate_url",
            "http://localhost:5000",
        )

        # location config
        self.location_source = self.StringConfig(self, "location_source", "browser")
        self.location_manual_lat = self.StringConfig(self, "location_manual_lat", "0.0")
        self.location_manual_lon = self.StringConfig(self, "location_manual_lon", "0.0")
        self.location_manual_alt = self.StringConfig(self, "location_manual_alt", "0.0")

        # stranger / trust config
        self.block_attachments_from_strangers = self.BoolConfig(
            self,
            "block_attachments_from_strangers",
            True,
        )
        self.block_all_from_strangers = self.BoolConfig(
            self,
            "block_all_from_strangers",
            False,
        )
        self.show_unknown_contact_banner = self.BoolConfig(
            self,
            "show_unknown_contact_banner",
            True,
        )

        # banishment config
        self.banished_effect_enabled = self.BoolConfig(
            self,
            "banished_effect_enabled",
            True,
        )
        self.banished_text = self.StringConfig(
            self,
            "banished_text",
            "BANISHED",
        )
        self.banished_color = self.StringConfig(
            self,
            "banished_color",
            "#dc2626",
        )
        self.message_font_size = self.IntConfig(self, "message_font_size", 14)
        self.message_icon_size = self.IntConfig(self, "message_icon_size", 28)
        self.ui_transparency = self.IntConfig(self, "ui_transparency", 0)
        self.ui_glass_enabled = self.BoolConfig(self, "ui_glass_enabled", True)
        self.message_outbound_bubble_color = self.StringConfig(
            self,
            "message_outbound_bubble_color",
            "#4f46e5",
        )
        self.message_inbound_bubble_color = self.StringConfig(
            self,
            "message_inbound_bubble_color",
            None,
        )
        self.message_failed_bubble_color = self.StringConfig(
            self,
            "message_failed_bubble_color",
            "#ef4444",
        )
        self.message_waiting_bubble_color = self.StringConfig(
            self,
            "message_waiting_bubble_color",
            "#e5e7eb",
        )

        # announce caps: max rows stored per aspect (oldest dropped). Default 1000.
        self.announce_max_stored_lxmf_delivery = self.IntConfig(
            self,
            "announce_max_stored_lxmf_delivery",
            1000,
        )
        self.announce_max_stored_nomadnetwork_node = self.IntConfig(
            self,
            "announce_max_stored_nomadnetwork_node",
            1000,
        )
        self.announce_max_stored_lxmf_propagation = self.IntConfig(
            self,
            "announce_max_stored_lxmf_propagation",
            1000,
        )
        # default API page size per aspect when limit query param omitted. Default 500.
        self.announce_fetch_limit_lxmf_delivery = self.IntConfig(
            self,
            "announce_fetch_limit_lxmf_delivery",
            500,
        )
        self.announce_fetch_limit_nomadnetwork_node = self.IntConfig(
            self,
            "announce_fetch_limit_nomadnetwork_node",
            500,
        )
        self.announce_fetch_limit_lxmf_propagation = self.IntConfig(
            self,
            "announce_fetch_limit_lxmf_propagation",
            500,
        )
        # lxst.telephony shares LXMF caps in announce_manager aspect mapping
        self.announce_search_max_fetch = self.IntConfig(
            self,
            "announce_search_max_fetch",
            2000,
        )
        self.discovered_interfaces_max_return = self.IntConfig(
            self,
            "discovered_interfaces_max_return",
            500,
        )

        # blackhole integration config
        self.blackhole_integration_enabled = self.BoolConfig(
            self,
            "blackhole_integration_enabled",
            True,
        )

        # csp config so users can set extra CSP sources for local offgrid environments (tile servers, etc.)
        self.csp_extra_connect_src = self.StringConfig(
            self,
            "csp_extra_connect_src",
            "",
        )
        self.csp_extra_img_src = self.StringConfig(self, "csp_extra_img_src", "")
        self.csp_extra_frame_src = self.StringConfig(self, "csp_extra_frame_src", "")
        self.csp_extra_script_src = self.StringConfig(self, "csp_extra_script_src", "")
        self.csp_extra_style_src = self.StringConfig(self, "csp_extra_style_src", "")

        self.nomad_render_markdown_enabled = self.BoolConfig(
            self,
            "nomad_render_markdown_enabled",
            True,
        )
        self.nomad_render_html_enabled = self.BoolConfig(
            self,
            "nomad_render_html_enabled",
            True,
        )
        self.nomad_render_plaintext_enabled = self.BoolConfig(
            self,
            "nomad_render_plaintext_enabled",
            True,
        )
        self.nomad_default_page_path = self.StringConfig(
            self,
            "nomad_default_page_path",
            "/page/index.mu",
        )

        self._migrate_legacy_announce_limit_keys()

    def get(self, key: str, default_value=None) -> str | None:
        return self.db.config.get(key, default_value)

    def set(self, key: str, value: str | None):
        self.db.config.set(key, value)

    def _migrate_legacy_announce_limit_keys(self):
        pairs = [
            ("announce_limit_lxmf_delivery", "announce_max_stored_lxmf_delivery"),
            (
                "announce_limit_nomadnetwork_node",
                "announce_max_stored_nomadnetwork_node",
            ),
            ("announce_limit_lxmf_propagation", "announce_max_stored_lxmf_propagation"),
        ]
        for old_key, new_key in pairs:
            old_val = self.db.config.get(old_key, default=None)
            new_val = self.db.config.get(new_key, default=None)
            if old_val is not None and new_val is None:
                self.db.config.set(new_key, old_val)

    class StringConfig:
        def __init__(self, manager, key: str, default_value: str | None = None):
            self.manager = manager
            self.key = key
            self.default_value = default_value

        def get(self, default_value: str = None) -> str | None:
            _default_value = default_value or self.default_value
            return self.manager.get(self.key, default_value=_default_value)

        def set(self, value: str | None):
            self.manager.set(self.key, value)

    class BoolConfig:
        def __init__(self, manager, key: str, default_value: bool = False):
            self.manager = manager
            self.key = key
            self.default_value = default_value

        def get(self) -> bool:
            config_value = self.manager.get(self.key, default_value=None)
            if config_value is None:
                return self.default_value
            return str(config_value).lower() == "true"

        def set(self, value: bool):
            self.manager.set(self.key, "true" if value else "false")

    class IntConfig:
        def __init__(self, manager, key: str, default_value: int | None = 0):
            self.manager = manager
            self.key = key
            self.default_value = default_value

        def get(self) -> int | None:
            config_value = self.manager.get(self.key, default_value=None)
            if config_value is None:
                return self.default_value
            try:
                return int(config_value)
            except (ValueError, TypeError):
                return self.default_value

        def set(self, value: int | None):
            if value is None:
                self.manager.db.config.delete(self.key)
            else:
                self.manager.db.config.set(self.key, str(value))
