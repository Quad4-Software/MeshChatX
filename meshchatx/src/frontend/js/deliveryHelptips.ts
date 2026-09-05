// SPDX-License-Identifier: 0BSD

export const DELIVERY_HELPTIP_THRESHOLDS: any = {
    selfAnnounceStaleSeconds: 86400,
    peerAnnounceStaleSeconds: 86400,
};

/**
 * Map HTTP send failure to a stable failure kind for tip selection.
 * @param {number | undefined} status
 * @param {string | undefined} message
 */
export function mapSendFailureKind(status, message) {
    const text = (message || "").toLowerCase();
    if (text.includes("could not recall")) {
        return "recall";
    }
    if (text.includes("preferred propagation node configured")) {
        return "no_propagation_node";
    }
    if (text.includes("path to preferred propagation") || text.includes("propagation node")) {
        if (text.includes("no path")) {
            return "no_path_propagation_node";
        }
    }
    if (text.includes("no path")) {
        return "no_path";
    }
    if (text.includes("invalid destination")) {
        return "invalid";
    }
    if (status === 503) {
        return "router_error";
    }
    return "unknown";
}

/**
 * @param {{ diagnostics?: object, failureKind?: string, message?: string }} input
 * @returns {{ id: string, severity: string, messageKey: string, params?: object }[]}
 */
export function buildDeliveryHelptips({ diagnostics, failureKind, message }) {
    if (!diagnostics || typeof diagnostics !== "object") {
        return [];
    }

    const tips = [];
    const self = diagnostics.self || {};
    const peerAnnounce = diagnostics.peer_announce || {};
    const path = diagnostics.path || {};
    const recall = diagnostics.recall || {};
    const prefs = diagnostics.delivery_prefs || {};
    const hint = diagnostics.failure_hint || failureKind;

    if (self.auto_announce_enabled === false) {
        tips.push({
            id: "self_announce_disabled",
            severity: "warning",
            messageKey: "helptips.self_announce_disabled",
        });
    }

    const selfStaleThreshold = DELIVERY_HELPTIP_THRESHOLDS.selfAnnounceStaleSeconds;
    if (self.seconds_since_last_announce == null || self.seconds_since_last_announce > selfStaleThreshold) {
        tips.push({
            id: "self_announce_stale",
            severity: "info",
            messageKey: "helptips.self_announce_stale",
        });
    }

    if (hint === "recall" || recall.identity_known === false) {
        tips.push({
            id: "recall_failed",
            severity: "warning",
            messageKey: "helptips.recall_failed",
        });
    }

    if (peerAnnounce.known === false) {
        tips.push({
            id: "peer_announce_missing",
            severity: "warning",
            messageKey: "helptips.peer_announce_missing",
        });
    }

    if (hint === "no_propagation_node") {
        tips.push({
            id: "no_propagation_node",
            severity: "warning",
            messageKey: "helptips.no_propagation_node",
        });
    }

    if (hint === "no_path_propagation_node") {
        tips.push({
            id: "no_path_propagation_node",
            severity: "warning",
            messageKey: "helptips.no_path_propagation_node",
        });
    }

    if (path.has_path === false && hint !== "no_path_propagation_node" && hint !== "no_propagation_node") {
        tips.push({
            id: "no_path",
            severity: "warning",
            messageKey: "helptips.no_path",
        });
    }

    if (path.path_stale === true && path.has_path === true) {
        tips.push({
            id: "path_stale",
            severity: "info",
            messageKey: "helptips.path_stale",
        });
    }

    if (path.path_unresponsive === true) {
        tips.push({
            id: "path_unresponsive",
            severity: "warning",
            messageKey: "helptips.path_unresponsive",
        });
    }

    const peerStaleThreshold = DELIVERY_HELPTIP_THRESHOLDS.peerAnnounceStaleSeconds;
    if (
        peerAnnounce.known === true &&
        peerAnnounce.age_seconds != null &&
        peerAnnounce.age_seconds > peerStaleThreshold
    ) {
        tips.push({
            id: "peer_announce_stale",
            severity: "info",
            messageKey: "helptips.peer_announce_stale",
        });
    }

    const stampCost = peerAnnounce.stamp_cost;
    if (typeof stampCost === "number" && stampCost > 0 && (hint === "router_error" || failureKind === "send_failed")) {
        tips.push({
            id: "stamp_cost",
            severity: "info",
            messageKey: "helptips.stamp_cost",
            params: { cost: stampCost },
        });
    }

    if (
        prefs.propagation_fallback === false &&
        (hint === "no_path" || hint === "router_error" || path.has_path === false)
    ) {
        tips.push({
            id: "propagation_off",
            severity: "info",
            messageKey: "helptips.propagation_off",
        });
    }

    if (hint === "opportunistic" || (message || "").toLowerCase().includes("opportunistic")) {
        tips.push({
            id: "opportunistic_waiting",
            severity: "info",
            messageKey: "helptips.opportunistic_waiting",
        });
    }

    return tips;
}
