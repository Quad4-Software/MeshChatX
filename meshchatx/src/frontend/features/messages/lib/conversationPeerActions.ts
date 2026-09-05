// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { isDestinationHash } from "../../../js/meshValidate.js";
import { t } from "../../../js/i18n.js";

type ApiClient = {
    get: (url: string, opts?: unknown) => Promise<{ data?: Record<string, unknown> }>;
    post: (url: string, body?: unknown, opts?: unknown) => Promise<{ data?: Record<string, unknown> }>;
    delete: (url: string) => Promise<{ data?: Record<string, unknown> }>;
};

export async function pingPeer(api: ApiClient, destinationHash: string): Promise<void> {
    const hash = String(destinationHash || "").trim();
    if (!hash) return;
    if (!isDestinationHash(hash)) {
        await DialogUtils.alert(t("messages.invalid_destination_hash_format"));
        return;
    }
    const pingToastKey = "conversation-ping";
    ToastUtils.loading(t("messages.ping_in_progress"), 0, pingToastKey);
    try {
        const response = await api.post(
            `/api/v1/ping/${hash}/lxmf.delivery`,
            {},
            { params: { timeout: 30 } }
        );
        const pingResult = (response.data?.ping_result || {}) as Record<string, unknown>;
        const rttMilliseconds = ((Number(pingResult.rtt) || 0) * 1000).toFixed(3);
        const info = [
            t("messages.ping_reply_from", { hash }),
            t("messages.duration", { duration: `${rttMilliseconds} ms` }),
            t("messages.hops_there", { count: pingResult.hops_there }),
            t("messages.hops_back", { count: pingResult.hops_back }),
        ];
        if (pingResult.quality != null) {
            info.push(t("messages.signal_quality", { quality: pingResult.quality }));
        }
        if (pingResult.rssi != null) {
            info.push(t("messages.rssi_val", { rssi: pingResult.rssi }));
        }
        if (pingResult.snr != null) {
            info.push(t("messages.snr_val", { snr: pingResult.snr }));
        }
        await DialogUtils.alert(info.join("\n"));
    } catch (error) {
        const message =
            (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
            t("messages.ping_failed");
        await DialogUtils.alert(message);
    } finally {
        ToastUtils.dismiss(pingToastKey);
    }
}

export async function banishPeer(api: ApiClient, destinationHash: string): Promise<boolean> {
    const hash = String(destinationHash || "").trim();
    if (!hash) return false;
    if (!(await DialogUtils.confirm(t("messages.banish_confirm")))) return false;
    try {
        await api.post("/api/v1/blocked-destinations", { destination_hash: hash });
        GlobalEmitter.emit("block-status-changed");
        await DialogUtils.alert(t("messages.user_banished"));
        return true;
    } catch {
        await DialogUtils.alert(t("messages.failed_banish_user"));
        return false;
    }
}

export async function unbanishPeer(api: ApiClient, destinationHash: string): Promise<boolean> {
    const hash = String(destinationHash || "").trim();
    if (!hash) return false;
    try {
        await api.delete(`/api/v1/blocked-destinations/${hash}`);
        GlobalEmitter.emit("block-status-changed");
        await DialogUtils.alert(t("banishment.banishment_lifted"));
        return true;
    } catch {
        await DialogUtils.alert(t("banishment.failed_lift_banishment"));
        return false;
    }
}

export async function deletePeerConversation(api: ApiClient, destinationHash: string): Promise<boolean> {
    const hash = String(destinationHash || "").trim();
    if (!hash) return false;
    if (!(await DialogUtils.confirm(t("messages.delete_history_confirm")))) return false;
    try {
        await api.delete(`/api/v1/lxmf-messages/conversation/${hash}`);
        return true;
    } catch {
        await DialogUtils.alert(t("messages.failed_delete_history"));
        return false;
    }
}

export async function addPeerContact(
    api: ApiClient,
    contact: { name?: string; hash: string; lxmfAddress?: string; lxstAddress?: string }
): Promise<boolean> {
    const remoteHash = String(contact.hash || "").trim();
    if (!remoteHash) return false;
    try {
        await api.post("/api/v1/telephone/contacts", {
            name: contact.name || remoteHash,
            remote_identity_hash: remoteHash,
            lxmf_address: contact.lxmfAddress || remoteHash,
            lxst_address: contact.lxstAddress || undefined,
        });
        ToastUtils.success(t("contacts.contact_added"));
        return true;
    } catch {
        ToastUtils.error(t("messages.failed_add_contact"));
        return false;
    }
}

export async function updatePeerDisplayName(
    api: ApiClient,
    destinationHash: string
): Promise<string | null> {
    const hash = String(destinationHash || "").trim();
    if (!hash) return null;
    const displayName = await DialogUtils.prompt(t("messages.enter_display_name"));
    if (displayName == null) return null;
    try {
        await api.post(`/api/v1/destination/${hash}/custom-display-name/update`, {
            display_name: displayName,
        });
        return displayName;
    } catch {
        await DialogUtils.alert(t("messages.failed_update_display_name"));
        return null;
    }
}
