// SPDX-License-Identifier: 0BSD

import { getMicronWasmRuntimeOverride } from "./MicronWasmRuntimeOverride.js";

/** @param {string|undefined|null} raw */
export function normalizeMicronWasmReleaseTag(raw) {
    if (raw == null) {
        return null;
    }
    const text = String(raw)
        .trim()
        .replace(/\.wasm$/i, "");
    if (!text) {
        return null;
    }
    // eslint-disable-next-line security/detect-unsafe-regex -- bounded semver token in filename or tag
    const embedded = text.match(/(?:^|[._-])v?(\d+\.\d+\.\d+(?:[-.+][\w.-]+)?)(?:[._-]|$)/i);
    if (embedded) {
        const ver = embedded[1];
        return ver.startsWith("v") || ver.startsWith("V") ? `v${ver.slice(1)}` : `v${ver}`;
    }
    // eslint-disable-next-line security/detect-unsafe-regex -- bounded semver token at string start
    const leading = text.match(/^v?(\d+\.\d+\.\d+(?:[-.+][\w.-]+)?)/i);
    if (leading) {
        const ver = leading[1];
        return ver.startsWith("v") || ver.startsWith("V") ? `v${ver.slice(1)}` : `v${ver}`;
    }
    return null;
}

export function bundledMicronWasmReleaseTag() {
    const fromEnv = import.meta.env.VITE_MICRON_PARSER_GO_RELEASE;
    if (typeof fromEnv === "string" && fromEnv.trim() !== "") {
        return normalizeMicronWasmReleaseTag(fromEnv.trim()) || fromEnv.trim();
    }
    return null;
}

/**
 * @param {{ overrideReleaseTag?: string|null }} [opts]
 * @returns {string|null}
 */
export function resolveMicronWasmReleaseLabel(opts: any = {}) {
    const overrideLabel = normalizeMicronWasmReleaseTag(opts.overrideReleaseTag);
    if (overrideLabel) {
        return overrideLabel;
    }
    return bundledMicronWasmReleaseTag();
}

/** @returns {Promise<string|null>} */
export async function getEffectiveMicronWasmReleaseLabel() {
    try {
        const override = await getMicronWasmRuntimeOverride();
        return resolveMicronWasmReleaseLabel({ overrideReleaseTag: override?.releaseTag ?? null });
    } catch {
        return resolveMicronWasmReleaseLabel();
    }
}

export const MICRON_WASM_OVERRIDE_CHANGED_EVENT = "micron-wasm-override-changed";
