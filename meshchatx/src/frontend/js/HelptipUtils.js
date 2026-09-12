// SPDX-License-Identifier: 0BSD

import { apiPath } from "./constants.js";
import ToastUtils from "./ToastUtils.js";
import { buildDeliveryHelptips, mapSendFailureKind } from "./deliveryHelptips.js";
import {
    deliveryHelptipToastKey,
    recordHelptipShownForPeer,
    shouldShowDeliveryHelptips,
    shouldShowHelptip,
    shouldShowHelptipForPeer,
} from "./helptipPolicy.js";

const pendingFetches = new Map();
const MAX_HELPTIP_DETAILS = 3;
const HELPTIP_TOAST_DURATION_MS = 8000;

const SEVERITY_ORDER = {
    warning: 0,
    info: 1,
};

async function fetchDeliveryDiagnostics(api, peerHash) {
    const response = await api.get(apiPath(`/destination/${peerHash}/delivery-diagnostics`));
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
    if (!peerHash || !shouldShowDeliveryHelptips(config) || !shouldShowHelptipForPeer(peerHash)) {
        return null;
    }

    const normalizedHash = (peerHash || "").toLowerCase();

    let snapshot = diagnostics;
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
