// SPDX-License-Identifier: 0BSD

import GlobalState from "../../../js/GlobalState.js";
import WebSocketConnection from "../../../js/WebSocketConnection.js";
import DialogUtils from "../../../js/DialogUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import Utils from "../../../js/Utils.js";
import { t } from "../../../js/i18n.js";
import {
    patchServerConfig,
    publishPatchedConfig,
    sanitizeColorConfigFields,
} from "../../../js/settings/settingsConfigService.js";

export const APPEARANCE_DEFAULT_CONFIG = {
    theme: "light",
    theme_preset: "default",
    accent_color: null,
    custom_canvas_color: null,
    custom_surface_color: null,
    messages_sidebar_position: "left",
    app_sidebar_layout: "grouped",
    message_font_size: 14,
    message_icon_size: 28,
    ui_transparency: 0,
    ui_glass_enabled: true,
    message_outbound_bubble_color: "#4f46e5",
    message_inbound_bubble_color: null,
    message_failed_bubble_color: "#ef4444",
    message_waiting_bubble_color: "#e5e7eb",
};

export async function resetAppearanceDefaults(api = window.api): Promise<Record<string, any> | null> {
    try {
        const updated = await patchServerConfig(APPEARANCE_DEFAULT_CONFIG, api);
        sanitizeColorConfigFields(updated);
        publishPatchedConfig(updated);
        return updated;
    } catch (e) {
        console.error("Failed to reset appearance defaults", e);
        ToastUtils.error(t("common.error"));
        return null;
    }
}

export function handleDetailedOutboundSendStatusChange(checked: boolean): void {
    GlobalState.detailedOutboundSendStatus = checked;
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem("meshchatx_detailed_outbound_send_status", checked ? "true" : "false");
        }
    } catch {
        // ignore localStorage errors in sandboxed environments
    }
}

export function handleOutboundTransferProgressEnabledChange(checked: boolean): void {
    GlobalState.outboundTransferProgressEnabled = checked;
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem("meshchatx_outbound_transfer_progress_enabled", checked ? "true" : "false");
        }
    } catch {
        // ignore localStorage errors in sandboxed environments
    }
}

export function handleMessageTimestampGroupingChange(checked: boolean): void {
    GlobalState.messageTimestampGroupingEnabled = checked;
    try {
        if (typeof localStorage !== "undefined") {
            localStorage.setItem("meshchatx_message_timestamp_grouping_enabled", checked ? "true" : "false");
        }
    } catch {
        // ignore localStorage errors in sandboxed environments
    }
}

export async function savePreferredPropagationNodeHash(
    config: Record<string, any>,
    showInvalidToast = false,
    api = window.api
): Promise<Record<string, any> | null> {
    const raw = config.lxmf_preferred_propagation_node_destination_hash;
    const trimmed = (raw || "").toString().trim();
    if (!trimmed) {
        config.lxmf_preferred_propagation_node_destination_hash = null;
        const updated = await patchServerConfig({ lxmf_preferred_propagation_node_destination_hash: null }, api);
        sanitizeColorConfigFields(updated);
        publishPatchedConfig({ ...config, ...updated });
        return updated;
    }
    const parsed = Utils.parseDestinationHash(trimmed);
    if (!parsed) {
        if (showInvalidToast) {
            ToastUtils.error(t("tools.propagation_nodes.invalid_hash"));
        }
        return null;
    }
    config.lxmf_preferred_propagation_node_destination_hash = parsed;
    const patch: Record<string, any> = {
        lxmf_preferred_propagation_node_destination_hash: parsed,
    };
    if (config.lxmf_preferred_propagation_node_auto_select) {
        config.lxmf_preferred_propagation_node_auto_select = false;
        patch.lxmf_preferred_propagation_node_auto_select = false;
    }
    try {
        const updated = await patchServerConfig(patch, api);
        sanitizeColorConfigFields(updated);
        publishPatchedConfig({ ...config, ...updated });
        return updated;
    } catch (e) {
        console.error("Failed to save preferred propagation node hash", e);
        ToastUtils.error(t("common.error"));
        return null;
    }
}

export async function flushArchivedPages(): Promise<void> {
    if (!(await DialogUtils.confirm(t("settings.flush_archived_pages_confirm")))) return;
    WebSocketConnection.send(JSON.stringify({ type: "nomadnet.page.archive.flush" }));
    ToastUtils.success(t("settings.archived_pages_flushed"));
}

export async function revokeTelemetryTrust(contact: any, api = window.api): Promise<boolean> {
    if (!contact?.id) return false;
    try {
        await api.patch(`/api/v1/telephone/contacts/${contact.id}`, {
            is_telemetry_trusted: false,
        });
        ToastUtils.success(t("app.telemetry_trust_revoked_alert"));
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message || t("common.error"));
        return false;
    }
}

/** Persist web UI IP allowlist via app security settings (not mesh config). */
export async function saveWebUiIpAllowlist(allowlist: string, api = window.api): Promise<Record<string, any> | null> {
    try {
        const response = await api.patch("/api/v1/server/security", {
            web_ui_ip_allowlist: allowlist,
        });
        ToastUtils.success(t("app.setting_auto_saved", { label: t("app.web_ui_ip_allowlist") }));
        return (response?.data as Record<string, any>) || null;
    } catch (e) {
        ToastUtils.error(t("common.save_failed"));
        console.error("Failed to save web UI IP allowlist", e);
        return null;
    }
}
