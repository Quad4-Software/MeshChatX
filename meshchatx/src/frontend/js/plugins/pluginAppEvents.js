// SPDX-License-Identifier: 0BSD

import { WS_EVENTS } from "../constants";

/**
 * Maps plugin hook names (manifest permissions.hooks entries) to the
 * WebSocket events that deliver them. A hook may fan out to several
 * WebSocket events (for example shell.session covers both RNSH and RNX).
 * Hook names are part of the plugin API and intentionally do not mirror
 * internal WebSocket event names.
 *
 * @type {Readonly<Record<string, readonly string[]>>}
 */
export const PLUGIN_HOOK_WS_EVENTS = Object.freeze({
    "lxmf.message.created": Object.freeze([WS_EVENTS.LXMF_MESSAGE_CREATED]),
    "lxmf.message.deleted": Object.freeze([WS_EVENTS.LXMF_MESSAGE_DELETED]),
    "lxmf.message.state": Object.freeze([WS_EVENTS.LXMF_MESSAGE_STATE_UPDATED]),
    "lxmf.delivery": Object.freeze([WS_EVENTS.LXMF_DELIVERY]),
    "lxmf.telemetry": Object.freeze([WS_EVENTS.LXMF_TELEMETRY]),
    "file.transfer.progress": Object.freeze([WS_EVENTS.RNCP_TRANSFER_PROGRESS]),
    "file.download.started": Object.freeze([WS_EVENTS.NOMADNET_FILE_DOWNLOAD]),
    "file.download.cancelled": Object.freeze([WS_EVENTS.NOMADNET_DOWNLOAD_CANCELLED]),
    "shell.session": Object.freeze([WS_EVENTS.RNSH_SESSION_CHANGE, WS_EVENTS.RNX_SESSION_CHANGE]),
    "shell.output": Object.freeze([WS_EVENTS.RNSH_OUTPUT, WS_EVENTS.RNX_OUTPUT]),
    "rrc.message": Object.freeze([WS_EVENTS.RRC_MESSAGE]),
});

/** Maximum serialized size of a hook payload forwarded to a plugin worker. */
export const PLUGIN_HOOK_PAYLOAD_MAX_CHARS = 65_536;

/**
 * Return the WebSocket event names that feed a plugin hook, or an empty
 * array for hooks delivered by the backend (for example announce.received).
 *
 * @param {string} hook
 * @returns {readonly string[]}
 */
export function wsEventsForPluginHook(hook) {
    return PLUGIN_HOOK_WS_EVENTS[hook] || [];
}

/**
 * @param {unknown} payload
 * @returns {boolean} true when the payload is small enough to forward
 */
export function pluginHookPayloadAllowed(payload) {
    try {
        return JSON.stringify(payload ?? null).length <= PLUGIN_HOOK_PAYLOAD_MAX_CHARS;
    } catch {
        return false;
    }
}
