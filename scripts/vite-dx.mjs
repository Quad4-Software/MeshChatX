// SPDX-License-Identifier: 0BSD

/**
 * Vite-serve developer experience helpers.
 * Production vite build must not depend on editor-only tooling.
 *
 * Set MESHCHAT_VITE_BUNDLED_DEV=1 to enable Vite experimental bundledDev mode.
 */

/**
 * @param {unknown} value
 * @returns {boolean}
 */
export function envFlagEnabled(value) {
    if (value === undefined || value === null || value === "") {
        return false;
    }
    return ["1", "true", "yes"].includes(String(value).toLowerCase());
}

/**
 * Editor for open-in-editor tooling. LAUNCH_EDITOR wins, else code.
 *
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string}
 */
export function detectLaunchEditor(env = process.env) {
    const explicit = env.LAUNCH_EDITOR;
    if (explicit !== undefined && String(explicit).trim() !== "") {
        return String(explicit).trim();
    }
    return "code";
}
