// SPDX-License-Identifier: 0BSD

import { getMicronWasmRuntimeOverride } from "./MicronWasmRuntimeOverride.js";

export function normalizeMicronWasmReleaseTag(raw: string | undefined | null): string | null {
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

export function bundledMicronWasmReleaseTag(): string | null {
    const fromEnv = import.meta.env.VITE_MICRON_PARSER_GO_RELEASE;
    if (typeof fromEnv === "string" && fromEnv.trim() !== "") {
        return normalizeMicronWasmReleaseTag(fromEnv.trim()) || fromEnv.trim();
    }
    return null;
}

export type ResolveMicronWasmReleaseLabelOpts = {
    overrideReleaseTag?: string | null;
};

export function resolveMicronWasmReleaseLabel(opts: ResolveMicronWasmReleaseLabelOpts = {}): string | null {
    const overrideLabel = normalizeMicronWasmReleaseTag(opts.overrideReleaseTag);
    if (overrideLabel) {
        return overrideLabel;
    }
    return bundledMicronWasmReleaseTag();
}

export async function getEffectiveMicronWasmReleaseLabel(): Promise<string | null> {
    try {
        const override = await getMicronWasmRuntimeOverride();
        return resolveMicronWasmReleaseLabel({ overrideReleaseTag: override?.releaseTag ?? null });
    } catch {
        return resolveMicronWasmReleaseLabel();
    }
}

export const MICRON_WASM_OVERRIDE_CHANGED_EVENT = "micron-wasm-override-changed";
