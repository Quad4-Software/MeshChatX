// SPDX-License-Identifier: 0BSD

/**
 * Vite-serve developer experience gates (Vue DevTools, open-in-editor).
 * Production vite build must not load these plugins.
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
 * Vue DevTools overlay is Vite serve only. Vitest, vite build, and e2e
 * (MESHCHAT_VUE_DEVTOOLS=0) stay off. Production bundles never include it.
 *
 * @param {{ command?: string, env?: NodeJS.ProcessEnv }} [options]
 * @returns {boolean}
 */
export function isVueDevToolsEnabled(options = {}) {
    const command = options.command;
    const env = options.env || process.env;
    if (command !== "serve") {
        return false;
    }
    if (env.VITEST) {
        return false;
    }
    const raw = env.MESHCHAT_VUE_DEVTOOLS;
    if (raw !== undefined && raw !== "") {
        return envFlagEnabled(raw);
    }
    return true;
}

/**
 * Editor for Vue DevTools open-in-editor. LAUNCH_EDITOR wins, else code.
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
