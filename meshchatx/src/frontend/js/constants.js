// @ts-check

/**
 * Shared frontend constants.
 *
 * Wire-contract strings (API prefix, WS event names), localStorage
 * keys, and emitter event names are defined once here. Add new values
 * here instead of scattering string literals through components.
 */

export const API_V1_PREFIX = "/api/v1";

/** Build an API path from the part after the version prefix. */
export function apiPath(path) {
    return `${API_V1_PREFIX}${path}`;
}

/** Server -> client WebSocket event names (used with onWsEvent). */
export const WS_EVENTS = Object.freeze({
    ANNOUNCE: "announce",
    APP_SESSIONS_UPDATED: "app.sessions.updated",
    CONFIG: "config",
    KEYBOARD_SHORTCUTS: "keyboard_shortcuts",
    LXMF_DELIVERY: "lxmf.delivery",
    LXMF_FORWARDING_RULES: "lxmf.forwarding.rules",
    LXMF_MESSAGE_CREATED: "lxmf_message_created",
    LXMF_MESSAGE_DELETED: "lxmf_message_deleted",
    LXMF_MESSAGE_STATE_UPDATED: "lxmf_message_state_updated",
    LXMF_TELEMETRY: "lxmf.telemetry",
    LXM_GENERATE_PAPER_URI_RESULT: "lxm.generate_paper_uri.result",
    LXM_INGEST_URI_RESULT: "lxm.ingest_uri.result",
    NOMADNET_DOWNLOAD_CANCELLED: "nomadnet.download.cancelled",
    NOMADNET_FILE_DOWNLOAD: "nomadnet.file.download",
    NOMADNET_PAGE_ARCHIVE_ADDED: "nomadnet.page.archive.added",
    NOMADNET_PAGE_ARCHIVES: "nomadnet.page.archives",
    NOMADNET_PAGE_DOWNLOAD: "nomadnet.page.download",
    PLUGIN_EVENT: "plugin.event",
    RETICULUM_RELOAD_STATUS: "reticulum_reload_status",
    RNCP_RECEIVE_COMPLETED: "rncp.receive.completed",
    RNCP_TRANSFER_PROGRESS: "rncp.transfer.progress",
    RNSH_OUTPUT: "rnsh.output",
    RNSH_SESSION_CHANGE: "rnsh.session.change",
    RNX_OUTPUT: "rnx.output",
    RNX_SESSION_CHANGE: "rnx.session.change",
    RRC_CHANGE: "rrc.change",
    RRC_MESSAGE: "rrc.message",
    RRC_SERVER_CHANGE: "rrc.server.change",
});

/** GlobalEmitter in-app event names. */
export const EMITTER_EVENTS = Object.freeze({
    BLOCK_STATUS_CHANGED: "block-status-changed",
    CHANGELOG_CLOSED: "changelog-closed",
    COMPOSE_NEW_MESSAGE: "compose-new-message",
    CONFIG_UPDATED: "config-updated",
    CONFIRM: "confirm",
    CONTACT_UPDATED: "contact-updated",
    IDENTITY_SWITCHED: "identity-switched",
    IDENTITY_SWITCHED_APPLY: "identity-switched-apply",
    IDENTITY_SWITCHING_ABORT: "identity-switching-abort",
    IDENTITY_SWITCHING_START: "identity-switching-start",
    KEYBOARD_SHORTCUT: "keyboard-shortcut",
    NOMADNET_FAVOURITES_LAYOUT_IMPORTED: "nomadnet-favourites-layout-imported",
    NOMAD_OPEN_NODE: "nomad-open-node",
    NOTIFICATIONS_CHANGED: "notifications-changed",
    OPEN_COMMAND_PALETTE: "open-command-palette",
    PROMPT: "prompt",
    REFRESH_CONVERSATIONS: "refresh-conversations",
    SHOW_CHANGELOG: "show-changelog",
    SHOW_TUTORIAL: "show-tutorial",
    SYNC_PROPAGATION_NODE: "sync-propagation-node",
    TELEPHONE_HISTORY_UPDATED: "telephone-history-updated",
    TOAST: "toast",
    TOAST_DISMISS: "toast-dismiss",
    TOAST_DISMISSED: "toast-dismissed",
    TUTORIAL_FINISHED: "tutorial-finished",
    WEBSOCKET_RECONNECTED: "websocket-reconnected",
});

/** localStorage key names. */
export const STORAGE_KEYS = Object.freeze({
    INTEGRITY_WARNING_DISMISSED: "integrity_warning_dismissed",
    MAP_ONBOARDING_SEEN: "map_onboarding_seen",
    MESSAGE_DRAFTS: "meshchat.drafts",
    COMPOSE_TRANSLATE_TARGET_LANG: "meshchatx.composeTranslateTargetLang",
    DETAILED_OUTBOUND_SEND_STATUS: "meshchatx_detailed_outbound_send_status",
    EXPOSURE_ACK_FIREWALL: "meshchatx_exposure_ack_firewall",
    EXPOSURE_ACK_VPN: "meshchatx_exposure_ack_vpn",
    FOLDERS_EXPANDED: "meshchatx_folders_expanded",
    INTERFACES_DISCOVERED_STATUS_FILTER: "meshchatx.interfaces.discoveredStatusFilter",
    INTERFACES_STATUS_FILTER: "meshchatx.interfaces.statusFilter",
    MAP_OFFLINE_MODE: "meshchatx.map.offlineMode",
    MESSAGE_TIMESTAMP_GROUPING_ENABLED: "meshchatx_message_timestamp_grouping_enabled",
    OPEN_AFTER_RELAUNCH: "meshchatx_open_after_relaunch",
    OUTBOUND_TRANSFER_PROGRESS_ENABLED: "meshchatx_outbound_transfer_progress_enabled",
    SETTINGS_MODE: "meshchatx_settings_mode",
    TRANSLATE_TARGET_LANG: "meshchatx.translateTargetLang",
    UI_THEME: "meshchatx_ui_theme",
    MICRON_EDITOR_CONTENT: "micron_editor_content",
});
