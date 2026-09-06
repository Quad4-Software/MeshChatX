// SPDX-License-Identifier: 0BSD

import ToastUtils from "./ToastUtils.js";
import { buildDeliveryHelptips, mapSendFailureKind, type DeliveryHelptip } from "./deliveryHelptips.js";
import { deliveryHelptipToastKey, shouldShowDeliveryHelptips, shouldShowHelptip } from "./helptipPolicy.js";
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

async function fetchDeliveryDiagnostics(
    api: Pick<ApiClient, "get">,
    peerHash: string
): Promise<Record<string, unknown> | null> {
    const response = await api.get(`/api/v1/destination/${peerHash}/delivery-diagnostics`);
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
    if (!peerHash || !shouldShowDeliveryHelptips(config)) {
        return null;
    }

    let snapshot = diagnostics ?? null;
    if (!snapshot) {
        try {
            snapshot = await fetchDeliveryDiagnostics(api, peerHash);
        } catch (e) {
            console.log(e);
            return null;
        }
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

    const titleKey =
        failureKind === "delivery_failed" ? "helptips.title_delivery_failed" : "helptips.title_send_failed";
    const details = visibleTips.map((tip) => i18n(tip.messageKey, tip.params));

    ToastUtils.helptips({
        title: i18n(titleKey),
        details,
        type: "warning",
        duration: 11000,
        key: deliveryHelptipToastKey(peerHash),
    });

    return {
        diagnostics: snapshot,
        tips: visibleTips,
        firstTipLine: details[0] ?? null,
    };
}

export default { showDeliveryHelptips };
