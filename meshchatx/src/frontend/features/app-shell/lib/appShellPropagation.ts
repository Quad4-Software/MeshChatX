// SPDX-License-Identifier: 0BSD

/**
 * Propagation node sync: start, poll, stop, inbound cancel, and status refresh.
 */

import DialogUtils from "../../../js/DialogUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { postRequestPath } from "../../../js/reticulumPathfinding.js";
import { PROPAGATION_SYNC_TOAST_KEY, PROPAGATION_SYNC_POLL_TIMEOUT_MS, ACTIVE_SYNC_STATES, apiClient } from "./appShellShared.js";
import type { AppShellState } from "./appShellState.svelte.js";

// Propagation node sync
// ------------------------------------------------------------------
export function propagationSyncStatusLabel(syncState: string | null | undefined): string {
    if (syncState == null || syncState === "") {
        return t("app.propagation_sync_state.unknown");
    }
    const key = `app.propagation_sync_state.${syncState}`;
    const translated = t(key);
    return translated !== key ? translated : t("app.propagation_sync_state.unknown");
}

export function propagationSyncLiveToastMessage(state: AppShellState): string {
    const status = state.propagationNodeStatus?.state ?? "unknown";
    const progress = Math.round(state.propagationNodeStatus?.progress ?? 0);
    return t("app.propagation_sync_live", {
        status: propagationSyncStatusLabel(status),
        progress,
    });
}

export async function syncPropagationNode(state: AppShellState): Promise<void> {
    // ask to stop syncing if already syncing
    if (state.isSyncingPropagationNode) {
        if (await DialogUtils.confirm(t("app.stop_sync_confirm"))) {
            await stopSyncingPropagationNode(state);
        }
        return;
    }

    state.userInitiatedPropagationSync = true;

    try {
        const preferredHash = state.config?.lxmf_preferred_propagation_node_destination_hash;
        if (preferredHash) {
            // Best-effort path priming. /sync also requests a path.
            try {
                await postRequestPath(apiClient(), preferredHash);
            } catch {
                // continue to sync
            }
        }
        await apiClient().post("/api/v1/lxmf/propagation-node/sync");
    } catch (e) {
        state.userInitiatedPropagationSync = false;
        const error = e as { response?: { data?: { message?: string; error?: string } } };
        ToastUtils.error(
            error.response?.data?.message ?? error.response?.data?.error ?? t("app.sync_error_generic")
        );
        return;
    }

    await updatePropagationNodeStatus(state);

    state.isPropagationSyncPolling = false;
    const pollStartedAt = Date.now();

    const poll = async (): Promise<void> => {
        if (state.isPropagationSyncPolling) {
            return;
        }
        state.isPropagationSyncPolling = true;
        try {
            await updatePropagationNodeStatus(state);
            if (state.isSyncingPropagationNode) {
                if (Date.now() - pollStartedAt > PROPAGATION_SYNC_POLL_TIMEOUT_MS) {
                    if (state.propagationSyncPollTimer != null) {
                        clearInterval(state.propagationSyncPollTimer);
                        state.propagationSyncPollTimer = null;
                    }
                    await stopSyncingPropagationNode(state);
                    state.userInitiatedPropagationSync = false;
                    ToastUtils.error(
                        t("app.sync_error", {
                            status: propagationSyncStatusLabel("path_timeout"),
                        })
                    );
                    return;
                }
                ToastUtils.loading(propagationSyncLiveToastMessage(state), 0, PROPAGATION_SYNC_TOAST_KEY);
                return;
            }
            if (state.propagationSyncPollTimer != null) {
                clearInterval(state.propagationSyncPollTimer);
                state.propagationSyncPollTimer = null;
            }
            state.userInitiatedPropagationSync = false;
            ToastUtils.dismiss(PROPAGATION_SYNC_TOAST_KEY);
            const status = state.propagationNodeStatus?.state;
            const messagesReceived = state.propagationNodeStatus?.messages_received ?? 0;
            const messagesStored = state.propagationNodeStatus?.messages_stored ?? 0;
            const deliveryConfirmations = state.propagationNodeStatus?.delivery_confirmations ?? 0;
            const messagesHidden = state.propagationNodeStatus?.messages_hidden ?? 0;
            if (status === "complete" || status === "idle") {
                const base = t("app.sync_complete", { count: messagesReceived });
                const details = `${messagesStored} stored, ${deliveryConfirmations} confirmations, ${messagesHidden} hidden`;
                ToastUtils.success(`${base} (${details})`);
            } else {
                ToastUtils.error(
                    t("app.sync_error", {
                        status: propagationSyncStatusLabel(status),
                    })
                );
            }
        } finally {
            state.isPropagationSyncPolling = false;
        }
    };

    if (state.isSyncingPropagationNode) {
        ToastUtils.loading(propagationSyncLiveToastMessage(state), 0, PROPAGATION_SYNC_TOAST_KEY);
        state.propagationSyncPollTimer = setInterval(() => void poll(), 500);
    } else {
        state.userInitiatedPropagationSync = false;
    }
    await poll();
}

export async function stopSyncingPropagationNode(state: AppShellState): Promise<void> {
    try {
        await apiClient().post("/api/v1/lxmf/propagation-node/stop-sync");
    } catch {
        // do nothing on error
    }
    if (state.propagationSyncPollTimer != null) {
        clearInterval(state.propagationSyncPollTimer);
        state.propagationSyncPollTimer = null;
    }
    state.isPropagationSyncPolling = false;
    state.userInitiatedPropagationSync = false;
    ToastUtils.dismiss(PROPAGATION_SYNC_TOAST_KEY);
    await updatePropagationNodeStatus(state);
}

export async function cancelInboundDeliveries(state: AppShellState): Promise<void> {
    const count = state.inboundDeliveryCount;
    if (count <= 0) {
        return;
    }
    if (!(await DialogUtils.confirm(t("app.cancel_inbound_confirm", { count })))) {
        return;
    }
    try {
        const response = await apiClient().post("/api/v1/lxmf/propagation-node/cancel-inbound", {});
        const cancelled = response?.data?.cancelled ?? 0;
        ToastUtils.success(t("app.cancel_inbound_done", { count: cancelled }));
        if (response?.data?.inbound_deliveries) {
            state.propagationNodeStatus = {
                ...(state.propagationNodeStatus || {}),
                inbound_delivery_count: response.data.inbound_delivery_count ?? 0,
                inbound_deliveries: response.data.inbound_deliveries,
            };
        } else {
            await updatePropagationNodeStatus(state);
        }
    } catch (e) {
        const error = e as { response?: { data?: { message?: string } } };
        ToastUtils.error(error.response?.data?.message ?? t("app.cancel_inbound_failed"));
    }
}

export async function updatePropagationNodeStatus(state: AppShellState): Promise<void> {
    try {
        const response = await apiClient().get("/api/v1/lxmf/propagation-node/status");
        state.propagationNodeStatus = response.data.propagation_node_status;
        const syncState = state.propagationNodeStatus?.state;
        if (state.userInitiatedPropagationSync && syncState && !ACTIVE_SYNC_STATES.includes(syncState)) {
            state.userInitiatedPropagationSync = false;
        }
    } catch {
        // do nothing on error
    }
}
