// SPDX-License-Identifier: 0BSD

/**
 * Pure policy for LXMF message OS notifications and in-app sound.
 * Open peer means any messages pane currently showing that destination.
 * Sound is suppressed only while that peer is open and the window is focused.
 * OS toasts fire whenever the window is backgrounded (minimized or unfocused).
 */

/**
 * Show a desktop/OS toast for incoming mail when the window is not in the
 * foreground. When minimized or blurred, toast for every eligible message.
 *
 * @param {object} opts
 * @param {boolean} [opts.isIncoming]
 * @param {boolean} [opts.sieveSuppress]
 * @param {boolean} [opts.dnd]
 * @param {boolean} [opts.hasFocus]
 * @param {boolean} [opts.userFacing]
 * @returns {boolean}
 */
export function shouldShowOsMessageNotification({
    isIncoming = false,
    sieveSuppress = false,
    dnd = false,
    hasFocus = true,
    userFacing = true,
}: any = {}) {
    if (dnd || sieveSuppress) {
        return false;
    }
    if (!isIncoming || !userFacing) {
        return false;
    }
    if (hasFocus) {
        return false;
    }
    return true;
}

/**
 * Play in-app alert for incoming mail unless DND or the user is already
 * reading that peer with the window focused. Unfocused or minimized windows
 * still get sound so alerts are not tied to foreground-only autoplay.
 *
 * @param {object} opts
 * @param {boolean} [opts.isIncoming]
 * @param {boolean} [opts.sieveSuppress]
 * @param {boolean} [opts.dnd]
 * @param {boolean} [opts.hasFocus]
 * @param {Iterable<string>|string[]|Set<string>|null} [opts.openDestinationHashes]
 * @param {string|null|undefined} [opts.sourceHash]
 * @param {boolean} [opts.userFacing]
 * @returns {boolean}
 */
export function shouldPlayMessageSound({
    isIncoming = false,
    sieveSuppress = false,
    dnd = false,
    hasFocus = true,
    openDestinationHashes = null,
    sourceHash = null,
    userFacing = true,
}: any = {}) {
    if (dnd || sieveSuppress) {
        return false;
    }
    if (!isIncoming || !userFacing) {
        return false;
    }
    const src = normalizeDestinationHash(sourceHash);
    if (hasFocus && src && isOpenDestination(src, openDestinationHashes)) {
        return false;
    }
    return true;
}

/**
 * Lightweight frontend mirror of backend user-facing LXMF filter for delivery events.
 * @param {object|null|undefined} lxmfMessage
 * @returns {boolean}
 */
export function isUserFacingLxmfDeliveryMessage(lxmfMessage) {
    if (!lxmfMessage || typeof lxmfMessage !== "object") {
        return false;
    }
    if (lxmfMessage.is_reaction === true) {
        return false;
    }
    const fields = lxmfMessage.fields;
    if (fields && typeof fields === "object") {
        const reaction = fields.reaction;
        if (reaction && typeof reaction === "object" && reaction.reaction_to) {
            return false;
        }
    }
    const title = typeof lxmfMessage.title === "string" ? lxmfMessage.title.trim() : "";
    const content = typeof lxmfMessage.content === "string" ? lxmfMessage.content.trim() : "";
    if (title || content) {
        return true;
    }
    if (fields && typeof fields === "object") {
        if (fields.image || fields.audio || fields.file_attachments) {
            return true;
        }
        const keys = Object.keys(fields);
        if (keys.length === 0) {
            return false;
        }
        if (keys.every((k) => k === "telemetry")) {
            return false;
        }
    }
    return false;
}

/**
 * Peer hash for an incoming LXMF delivery payload (conversation key).
 * @param {object|null|undefined} json
 * @returns {string}
 */
export function deliverySourceHash(json) {
    if (!json || typeof json !== "object") {
        return "";
    }
    const msg = json.lxmf_message;
    if (msg && typeof msg === "object") {
        const fromMsg = normalizeDestinationHash(msg.source_hash);
        if (fromMsg) {
            return fromMsg;
        }
    }
    return normalizeDestinationHash(json.remote_identity_hash);
}

/**
 * @param {string|null|undefined} hash
 * @returns {string}
 */
export function normalizeDestinationHash(hash) {
    if (hash === undefined || hash === null) {
        return "";
    }
    return String(hash).trim().toLowerCase();
}

/**
 * @param {string} sourceHash
 * @param {Iterable<string>|string[]|Set<string>|null|undefined} openDestinationHashes
 * @returns {boolean}
 */
export function isOpenDestination(sourceHash, openDestinationHashes) {
    const src = normalizeDestinationHash(sourceHash);
    if (!src || !openDestinationHashes) {
        return false;
    }
    for (const h of openDestinationHashes) {
        if (normalizeDestinationHash(h) === src) {
            return true;
        }
    }
    return false;
}
