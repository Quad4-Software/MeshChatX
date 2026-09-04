// SPDX-License-Identifier: 0BSD

/**
 * Read a solved ALTCHA payload from the widget DOM or in-memory value.
 * ALTCHA widget v3 does not expose getPayload. The solved token lives in a
 * hidden input named after the widget name attribute (default "altcha").
 * @param {HTMLElement | null | undefined} widget
 * @param {string} [inputName="altcha"]
 * @returns {string | null}
 */
export function readAltchaPayloadFromWidget(widget, inputName = "altcha") {
    if (!widget) {
        return null;
    }
    const name = typeof inputName === "string" && inputName ? inputName : "altcha";
    const roots = [widget];
    if (widget.shadowRoot) {
        roots.push(widget.shadowRoot);
    }
    for (const root of roots) {
        if (typeof root.querySelectorAll !== "function") {
            continue;
        }
        const inputs = root.querySelectorAll("input");
        for (const input of inputs) {
            if (input.getAttribute("name") === name && typeof input.value === "string" && input.value.trim()) {
                return input.value.trim();
            }
        }
        for (const input of inputs) {
            if (input.getAttribute("type") === "hidden" && typeof input.value === "string" && input.value.trim()) {
                return input.value.trim();
            }
        }
    }
    return null;
}

/**
 * Payload from an ALTCHA verified or statechange CustomEvent.
 * @param {Event | { detail?: { payload?: unknown, state?: unknown } } | null | undefined} event
 * @returns {string | null}
 */
export function altchaPayloadFromEvent(event) {
    const detail = event && typeof event === "object" ? event.detail : null;
    if (!detail || typeof detail !== "object") {
        return null;
    }
    const payload = detail.payload;
    if (typeof payload === "string" && payload.trim()) {
        return payload.trim();
    }
    return null;
}

/**
 * Ensure a payload exists, running widget.verify() when needed.
 * @param {HTMLElement | null | undefined} widget
 * @param {string | null | undefined} existingPayload
 * @param {{ inputName?: string }} [options]
 * @returns {Promise<string | null>}
 */
export async function ensureAltchaPayload(widget, existingPayload, options = {}) {
    if (typeof existingPayload === "string" && existingPayload.trim()) {
        return existingPayload.trim();
    }
    const inputName = options.inputName || "altcha";
    const fromDom = readAltchaPayloadFromWidget(widget, inputName);
    if (fromDom) {
        return fromDom;
    }
    if (!widget || typeof widget.verify !== "function") {
        return null;
    }
    try {
        const result = await widget.verify();
        if (result && typeof result.payload === "string" && result.payload.trim()) {
            return result.payload.trim();
        }
    } catch {
        return readAltchaPayloadFromWidget(widget, inputName);
    }
    return readAltchaPayloadFromWidget(widget, inputName);
}
