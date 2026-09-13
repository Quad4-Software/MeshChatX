// SPDX-License-Identifier: 0BSD

import { apiPath } from "./constants.js";
import ToastUtils from "./ToastUtils.js";
import { buildDeliveryHelptips, mapSendFailureKind, type DeliveryHelptip } from "./deliveryHelptips.js";
import {
    deliveryHelptipToastKey,
    recordHelptipShownForPeer,
    shouldShowDeliveryHelptips,
    shouldShowHelptip,
    shouldShowHelptipForPeer,
} from "./helptipPolicy.js";
import type { ApiClient } from "./apiClient.js";

export type DeliveryFailureKind = "send_failed" | "delivery_failed";

export type ShowDeliveryHelptipsOptions = {
    api: Pick<ApiClient, "get">;
    peerHash: string;
    failureKind: DeliveryFailureKind;
    diagnostics?: Record<string, unknown> | null;
    status?: number;
    message?: string;
    config?: Record<string, unknown> | null;
    i18n: (key: string, params?: Record<string, unknown>) => string;
};

export type ShowDeliveryHelptipsResult = {
    diagnostics: Record<string, unknown> | null;
    tips: DeliveryHelptip[];
    firstTipLine: string | null;
} | null;

const pendingFetches = new Map<string, Promise<Record<string, unknown> | null>>();
const MAX_HELPTIP_DETAILS = 3;
const HELPTIP_TOAST_DURATION_MS = 8000;

const SEVERITY_ORDER: Record<string, number> = {
    warning: 0,
    info: 1,
};

async function fetchDeliveryDiagnostics(
    api: Pick<ApiClient, "get">,
    peerHash: string
): Promise<Record<string, unknown> | null> {
    const response = await api.get(apiPath(`/destination/${peerHash}/delivery-diagnostics`));
    return (response?.data as Record<string, unknown> | null | undefined) ?? null;
}

export async function showDeliveryHelptips({
    api,
    peerHash,
    failureKind,
    diagnostics,
    status,
    message,
    config,
    i18n,
}: ShowDeliveryHelptipsOptions): Promise<ShowDeliveryHelptipsResult> {
    if (!peerHash || !shouldShowDeliveryHelptips(config) || !shouldShowHelptipForPeer(peerHash)) {
        return null;
    }

    const normalizedHash = (peerHash || "").toLowerCase();

    let snapshot = diagnostics ?? null;
    if (!snapshot) {
        const inFlight = pendingFetches.get(normalizedHash);
        if (inFlight) {
            snapshot = await inFlight;
        } else {
            const promise = fetchDeliveryDiagnostics(api, peerHash)
                .then((result) => {
                    return result;
                })
                .finally(() => {
                    pendingFetches.delete(normalizedHash);
                });
            pendingFetches.set(normalizedHash, promise);
            snapshot = await promise;
        }
    }

    if (!snapshot) {
        return null;
    }

    const mappedKind = failureKind === "send_failed" ? mapSendFailureKind(status, message) : failureKind;
    const tips = buildDeliveryHelptips({
        diagnostics: snapshot,
        failureKind: mappedKind,
        message,
    });
    const visibleTips = tips.filter((tip) => shouldShowHelptip(peerHash, tip.id));
    if (visibleTips.length === 0) {
        return { diagnostics: snapshot, tips: [], firstTipLine: null };
    }

    recordHelptipShownForPeer(peerHash);

    const sortedTips = visibleTips.slice().sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
    const cappedTips = sortedTips.slice(0, MAX_HELPTIP_DETAILS);
    const details = cappedTips.map((tip) => i18n(tip.messageKey, tip.params));

    const titleKey =
        failureKind === "delivery_failed" ? "helptips.title_delivery_failed" : "helptips.title_send_failed";

    ToastUtils.helptips({
        title: i18n(titleKey),
        details,
        type: "warning",
        duration: HELPTIP_TOAST_DURATION_MS,
        key: deliveryHelptipToastKey(peerHash),
    });

    return {
        diagnostics: snapshot,
        tips: visibleTips,
        firstTipLine: details[0] ?? null,
    };
}

export function resetHelptipFetchesForTests() {
    pendingFetches.clear();
}

export default { showDeliveryHelptips, resetHelptipFetchesForTests };
