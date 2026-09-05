// SPDX-License-Identifier: 0BSD

import ToastUtils from "./ToastUtils.js";
import { buildDeliveryHelptips, mapSendFailureKind } from "./deliveryHelptips.js";
import { deliveryHelptipToastKey, shouldShowDeliveryHelptips, shouldShowHelptip } from "./helptipPolicy.js";

async function fetchDeliveryDiagnostics(api, peerHash) {
    const response = await api.get(`/api/v1/destination/${peerHash}/delivery-diagnostics`);
    return response?.data ?? null;
}

/**
 * @param {object} options
 * @param {object} options.api
 * @param {string} options.peerHash
 * @param {"send_failed"|"delivery_failed"} options.failureKind
 * @param {object | null | undefined} [options.diagnostics]
 * @param {number | undefined} [options.status]
 * @param {string | undefined} [options.message]
 * @param {object | null | undefined} [options.config]
 * @param {(key: string, params?: object) => string} options.i18n
 */
export async function showDeliveryHelptips({ api, peerHash, failureKind, diagnostics, status, message, config, i18n }) {
    if (!peerHash || !shouldShowDeliveryHelptips(config)) {
        return null;
    }

    let snapshot = diagnostics;
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
