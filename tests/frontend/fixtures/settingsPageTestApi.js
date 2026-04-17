import { vi } from "vitest";

/**
 * Mirrors meshchat `get_config_dict` keys used by SettingsPage so PATCH merges stay realistic.
 *
 * @param {Record<string, unknown>} [overrides]
 * @returns {Record<string, unknown>}
 */
export function buildFullServerConfig(overrides = {}) {
    return {
        display_name: "Test User",
        identity_hash: "abc123",
        identity_public_key: "00",
        lxmf_address_hash: "def456",
        telephone_address_hash: null,
        is_transport_enabled: false,
        auto_announce_enabled: false,
        auto_announce_interval_seconds: 0,
        last_announced_at: null,
        theme: "dark",
        language: "en",
        auto_resend_failed_messages_when_announce_received: true,
        allow_auto_resending_failed_messages_with_attachments: false,
        auto_send_failed_messages_to_propagation_node: false,
        show_suggested_community_interfaces: true,
        lxmf_delivery_transfer_limit_in_bytes: 10_000_000,
        lxmf_propagation_transfer_limit_in_bytes: 256_000,
        lxmf_propagation_sync_limit_in_bytes: 10_240_000,
        lxmf_local_propagation_node_enabled: false,
        lxmf_local_propagation_node_address_hash: "localhash",
        lxmf_preferred_propagation_node_destination_hash: "",
        lxmf_preferred_propagation_node_auto_select: false,
        lxmf_preferred_propagation_node_auto_sync_interval_seconds: 3600,
        lxmf_preferred_propagation_node_last_synced_at: null,
        lxmf_user_icon_name: "account",
        lxmf_user_icon_foreground_colour: "#111827",
        lxmf_user_icon_background_colour: "#e5e7eb",
        lxmf_inbound_stamp_cost: 8,
        lxmf_propagation_node_stamp_cost: 16,
        page_archiver_enabled: false,
        page_archiver_max_versions: 5,
        archives_max_storage_gb: 1,
        backup_max_count: 5,
        crawler_enabled: false,
        crawler_max_retries: 3,
        crawler_retry_delay_seconds: 30,
        crawler_max_concurrent: 2,
        auth_enabled: false,
        voicemail_enabled: false,
        voicemail_greeting: "",
        voicemail_auto_answer_delay_seconds: 0,
        voicemail_max_recording_seconds: 120,
        voicemail_tts_speed: 1,
        voicemail_tts_pitch: 1,
        voicemail_tts_voice: "",
        voicemail_tts_word_gap: 0,
        custom_ringtone_enabled: false,
        ringtone_filename: "",
        ringtone_preferred_id: null,
        ringtone_volume: 50,
        map_offline_enabled: false,
        map_mbtiles_dir: "",
        map_tile_cache_enabled: true,
        map_default_lat: "0",
        map_default_lon: "0",
        map_default_zoom: 2,
        map_tile_server_url: "",
        map_nominatim_api_url: "",
        do_not_disturb_enabled: false,
        telephone_allow_calls_from_contacts_only: false,
        telephone_audio_profile_id: null,
        telephone_web_audio_enabled: true,
        telephone_web_audio_allow_fallback: true,
        call_recording_enabled: false,
        block_attachments_from_strangers: true,
        block_all_from_strangers: false,
        show_unknown_contact_banner: true,
        warn_on_stranger_links: true,
        banished_effect_enabled: true,
        banished_text: "BANISHED",
        banished_color: "#dc2626",
        message_font_size: 14,
        messages_sidebar_position: "left",
        message_icon_size: 28,
        ui_transparency: 0,
        ui_glass_enabled: true,
        message_outbound_bubble_color: "#4f46e5",
        message_inbound_bubble_color: null,
        message_failed_bubble_color: "#ef4444",
        message_waiting_bubble_color: "#e5e7eb",
        translator_enabled: false,
        libretranslate_url: "http://localhost:5000",
        desktop_open_calls_in_separate_window: false,
        desktop_hardware_acceleration_enabled: true,
        blackhole_integration_enabled: true,
        announce_max_stored_lxmf_delivery: 1000,
        announce_max_stored_nomadnetwork_node: 1000,
        announce_max_stored_lxmf_propagation: 1000,
        announce_fetch_limit_lxmf_delivery: 500,
        announce_fetch_limit_nomadnetwork_node: 500,
        announce_fetch_limit_lxmf_propagation: 500,
        announce_search_max_fetch: 2000,
        discovered_interfaces_max_return: 500,
        csp_extra_connect_src: "",
        csp_extra_img_src: "",
        csp_extra_frame_src: "",
        csp_extra_script_src: "",
        csp_extra_style_src: "",
        telephone_tone_generator_enabled: true,
        telephone_tone_generator_volume: 50,
        location_source: "browser",
        location_manual_lat: "0.0",
        location_manual_lon: "0.0",
        location_manual_alt: "0.0",
        telemetry_enabled: false,
        nomad_render_markdown_enabled: true,
        nomad_render_html_enabled: true,
        nomad_render_plaintext_enabled: true,
        nomad_default_page_path: "/page/index.mu",
        gitea_base_url: "https://git.quad4.io",
        docs_download_urls: "",
        ...overrides,
    };
}

/**
 * @param {{ current: Record<string, unknown> }} serverConfigRef
 */
export function createWindowApi(serverConfigRef) {
    return {
        get: vi.fn().mockImplementation((url) => {
            if (String(url).includes("/api/v1/config")) {
                return Promise.resolve({ data: { config: { ...serverConfigRef.current } } });
            }
            if (String(url).includes("/api/v1/telemetry/trusted-peers")) {
                return Promise.resolve({ data: { trusted_peers: [] } });
            }
            if (String(url).includes("/api/v1/stickers/export")) {
                return Promise.resolve({ data: { stickers: [] } });
            }
            if (String(url).includes("/api/v1/stickers") && !String(url).includes("export")) {
                return Promise.resolve({ data: { stickers: [] } });
            }
            if (String(url).includes("/api/v1/maintenance/messages/export")) {
                return Promise.resolve({ data: { messages: [] } });
            }
            if (String(url).includes("/api/v1/lxmf/folders/export")) {
                return Promise.resolve({ data: { folders: [] } });
            }
            return Promise.resolve({ data: {} });
        }),
        patch: vi.fn().mockImplementation((url, body) => {
            serverConfigRef.current = { ...serverConfigRef.current, ...body };
            return Promise.resolve({ data: { config: { ...serverConfigRef.current } } });
        }),
        post: vi.fn().mockResolvedValue({ data: { message: "ok" } }),
        delete: vi.fn().mockResolvedValue({ data: {} }),
    };
}
