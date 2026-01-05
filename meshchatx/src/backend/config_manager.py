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
        self.lxmf_preferred_propagation_node_destination_hash = self.StringConfig(
            self,
            "lxmf_preferred_propagation_node_destination_hash",
            None,
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
            self, "gitea_base_url", "https://git.quad4.io"
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
            self, "voicemail_tts_voice", "en-us+f3"
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

        # translator config
        self.translator_enabled = self.BoolConfig(self, "translator_enabled", False)
        self.libretranslate_url = self.StringConfig(
            self,
            "libretranslate_url",
            "http://localhost:5000",
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

        # blackhole integration config
        self.blackhole_integration_enabled = self.BoolConfig(
            self,
            "blackhole_integration_enabled",
            True,
        )

    def get(self, key: str, default_value=None) -> str | None:
        return self.db.config.get(key, default_value)

    def set(self, key: str, value: str | None):
        self.db.config.set(key, value)

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

        def set(self, value: int):
            self.manager.set(self.key, str(value))
