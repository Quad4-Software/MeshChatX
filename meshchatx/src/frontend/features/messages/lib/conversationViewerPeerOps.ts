// SPDX-License-Identifier: 0BSD

import type { ApiClient } from "../../../js/apiClient.js";

type Api = ApiClient | {
    post: (url: string, body?: any, opts?: any) => Promise<{ data?: any }>;
    delete: (url: string, opts?: any) => Promise<any>;
};

type DialogUtilsLike = {
    alert: (message: string) => Promise<void> | void;
    confirm: (message: string) => Promise<boolean> | boolean;
};

type ToastUtilsLike = {
    loading: (message: string, duration?: number, key?: string) => void;
    dismiss: (key: string) => void;
};

type TFn = (key: string, values?: Record<string, unknown>) => string;

export async function pingPeerDestination(opts: {
    api: Api;
    destinationHash: string;
    t: TFn;
    DialogUtils: DialogUtilsLike;
    ToastUtils: ToastUtilsLike;
}): Promise<void> {
    const { api, destinationHash, t, DialogUtils, ToastUtils } = opts;
    if (destinationHash.length !== 32 || !/^[0-9a-fA-F]+$/.test(destinationHash)) {
        await DialogUtils.alert(t("messages.invalid_destination_hash_format"));
        return;
    }
    const pingToastKey = "conversation-ping";
    ToastUtils.loading(t("messages.ping_in_progress"), 0, pingToastKey);
    try {
        const response = await api.post(
            `/api/v1/ping/${destinationHash}/lxmf.delivery`,
            {},
            { params: { timeout: 30 } }
        );
        const pingData = response.data as { ping_result?: Record<string, unknown> } | undefined;
        const pingResult = pingData?.ping_result || {};
        const rttMilliseconds = ((Number(pingResult.rtt) || 0) * 1000).toFixed(3);
        const info = [
            t("messages.ping_reply_from", { hash: destinationHash }),
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

export async function banishPeerDestination(opts: {
    api: Api;
    destinationHash: string;
    t: TFn;
    DialogUtils: DialogUtilsLike;
    emitBlockChanged: () => void;
}): Promise<void> {
    const { api, destinationHash, t, DialogUtils, emitBlockChanged } = opts;
    if (!(await DialogUtils.confirm(t("messages.banish_confirm")))) return;
    try {
        await api.post("/api/v1/blocked-destinations", { destination_hash: destinationHash });
        emitBlockChanged();
        await DialogUtils.alert(t("messages.user_banished"));
    } catch {
        await DialogUtils.alert(t("messages.failed_banish_user"));
    }
}

export async function unbanishPeerDestination(opts: {
    api: Api;
    destinationHash: string;
    t: TFn;
    DialogUtils: DialogUtilsLike;
    emitBlockChanged: () => void;
}): Promise<void> {
    const { api, destinationHash, t, DialogUtils, emitBlockChanged } = opts;
    try {
        await api.delete(`/api/v1/blocked-destinations/${destinationHash}`);
        emitBlockChanged();
        await DialogUtils.alert(t("banishment.banishment_lifted"));
    } catch {
        await DialogUtils.alert(t("banishment.failed_lift_banishment"));
    }
}

export async function deletePeerConversationHistory(opts: {
    api: Api;
    destinationHash: string;
    t: TFn;
    DialogUtils: DialogUtilsLike;
    onDone: () => void;
}): Promise<void> {
    const { api, destinationHash, t, DialogUtils, onDone } = opts;
    if (!(await DialogUtils.confirm(t("messages.delete_history_confirm")))) return;
    try {
        await api.delete(`/api/v1/lxmf-messages/conversation/${destinationHash}`);
        onDone();
    } catch {
        await DialogUtils.alert(t("messages.failed_delete_history"));
    }
}
