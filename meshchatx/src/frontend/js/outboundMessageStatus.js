// SPDX-License-Identifier: 0BSD AND MIT
/**
 * Outbound LXMF bubble status icons and i18n title keys.
 *
 * Backend emits API strings from LXMF.LXMessage via convert_lxmf_state_to_string
 * and convert_lxmf_method_to_string. Propagation is a method, never a state.
 */

const SENT_LIKE_STATES = new Set(["sent", "propagated", "unknown"]);

/**
 * @param {{ state?: string, method?: string } | null | undefined} lxmfMessage
 * @returns {string} MDI kebab icon name
 */
export function outboundBubbleStatusIconName(lxmfMessage) {
    if (!lxmfMessage) {
        return "check";
    }
    const state = lxmfMessage.state;
    const method = lxmfMessage.method;
    if (state === "delivered") {
        if (method === "propagated") {
            return "email-check-outline";
        }
        if (method === "paper") {
            return "note-check-outline";
        }
        return "check-all";
    }
    if (SENT_LIKE_STATES.has(state)) {
        if (method === "propagated") {
            return "email-outline";
        }
        if (method === "paper") {
            return "note-outline";
        }
        return "check";
    }
    return "check";
}

/**
 * @param {{ state?: string, method?: string } | null | undefined} lxmfMessage
 * @returns {string | null} i18n key under messages.*, or null when no title
 */
export function outboundBubbleStatusTitleKey(lxmfMessage) {
    if (!lxmfMessage) {
        return null;
    }
    if (lxmfMessage.state === "delivered") {
        if (lxmfMessage.method === "propagated") {
            return "messages.outbound_delivered_propagated";
        }
        return "messages.outbound_delivered";
    }
    if (lxmfMessage.method === "propagated") {
        return "messages.outbound_on_propagation_node";
    }
    return "messages.outbound_sent_network";
}

/**
 * Opportunistic FAILED is deferred wait in the UI, not a hard failure badge.
 * @param {{ state?: string, method?: string } | null | undefined} lxmfMessage
 */
export function isOpportunisticDeferredDelivery(lxmfMessage) {
    if (!lxmfMessage) {
        return false;
    }
    return lxmfMessage.method === "opportunistic" && lxmfMessage.state === "failed";
}
