// SPDX-License-Identifier: 0BSD
/**
 * NomadNet page display mode for small screens.
 *
 * "fit" scales the rendered page so the widest line matches the viewport
 * width. "scroll" keeps natural size and lets the frame scroll sideways.
 * The mode is persisted in localStorage and pushed into each sandboxed
 * renderer frame through postMessage, so the frame itself needs no storage.
 */

export const NOMAD_DISPLAY_MODE_KEY = "mcx.nomad-display-mode";
export const NOMAD_DISPLAY_MODE_EVENT = "mcx-nomad-display-mode-changed";
export const NOMAD_DISPLAY_MODES = ["fit", "scroll"];

const MIN_SCALE = 0.05;

export function normalizeNomadDisplayMode(value) {
    return NOMAD_DISPLAY_MODES.includes(value) ? value : null;
}

export function getNomadDisplayMode() {
    try {
        return normalizeNomadDisplayMode(window.localStorage.getItem(NOMAD_DISPLAY_MODE_KEY)) || "fit";
    } catch {
        return "fit";
    }
}

export function setNomadDisplayMode(mode) {
    const normalized = normalizeNomadDisplayMode(mode);
    if (!normalized) return getNomadDisplayMode();
    try {
        window.localStorage.setItem(NOMAD_DISPLAY_MODE_KEY, normalized);
    } catch {
        // Private browsing can deny storage. The mode still applies in memory.
    }
    window.dispatchEvent(new CustomEvent(NOMAD_DISPLAY_MODE_EVENT, { detail: normalized }));
    return normalized;
}

/**
 * Scale factor that shrinks content of naturalWidth to fit availWidth.
 * Never scales up and never below the legibility floor.
 */
export function computeNomadFitScale(naturalWidth, availWidth) {
    if (!Number.isFinite(naturalWidth) || !Number.isFinite(availWidth)) return 1;
    if (naturalWidth <= 0 || availWidth <= 0 || naturalWidth <= availWidth) return 1;
    return Math.max(MIN_SCALE, availWidth / naturalWidth);
}
