// SPDX-License-Identifier: 0BSD

import { mdiIconState } from "./mdiIconState.svelte.js";
import { MDI_ICON_NAMES, MDI_NAME_SET, MDI_USED_PATHS } from "./generated/mdiIconData.js";

export const DEFAULT_RRC_HUB_ICON = "forum-outline";

const MDI_KEY_ALIASES: Record<string, string> = {
    mdiRoute: "mdiRoutes",
    mdiEmailSendOutline: "mdiSendOutline",
};

const MATERIAL_SYMBOL_ALIASES: Record<string, string> = {
    "bug-report": "bug-outline",
    "smart-toy": "robot-outline",
    "robot-2": "robot-outline",
    "emoji-objects": "lightbulb-on",
};

type MdiNamespace = Record<string, string>;

let fullMdi: MdiNamespace | null = null;
let fullMdiPromise: Promise<MdiNamespace | null> | null = null;

/**
 * Lazily import the full @mdi/js path data (~2.7 MB chunk). Icons not in the
 * used subset resolve after this resolves and mdiIconState.fullReady flips.
 */
export function ensureFullMdi(): Promise<MdiNamespace | null> {
    if (fullMdi) {
        return Promise.resolve(fullMdi);
    }
    if (!fullMdiPromise) {
        fullMdiPromise = import("@mdi/js")
            .then((mod) => {
                fullMdi = (mod.default || mod) as MdiNamespace;
                mdiIconState.fullReady = true;
                return fullMdi;
            })
            .catch(() => null);
    }
    return fullMdiPromise;
}

function mdiKeyToListName(key: string): string {
    return key
        .replace(/^mdi/, "")
        .replace(/([a-z])([A-Z])/g, "$1-$2")
        .toLowerCase();
}

function mdiKeyExists(key: string): boolean {
    return MDI_NAME_SET.has(mdiKeyToListName(key));
}

export function buildMdiIconNames() {
    return MDI_ICON_NAMES.slice();
}

export function isValidMdiIconName(name) {
    if (typeof name !== "string" || !name) {
        return false;
    }
    const trimmed = name.trim().toLowerCase();
    if (!isKebabCaseIconName(trimmed)) {
        return false;
    }
    return MDI_NAME_SET.has(trimmed);
}

export function normalizeMdiIconName(name) {
    if (name == null || (typeof name === "string" && !name.trim())) {
        return null;
    }
    const trimmed = String(name).trim().toLowerCase();
    return isValidMdiIconName(trimmed) ? trimmed : null;
}

function isKebabCaseIconName(name) {
    if (!name || name.length > 64) {
        return false;
    }
    if (name.startsWith("-") || name.endsWith("-") || name.includes("--")) {
        return false;
    }
    for (let i = 0; i < name.length; i++) {
        const c = name.charCodeAt(i);
        if (c === 45) {
            continue;
        }
        if ((c >= 48 && c <= 57) || (c >= 97 && c <= 122)) {
            continue;
        }
        return false;
    }
    return true;
}

function splitIconParts(name) {
    return name.split(/[-_]/).filter((word) => word.length > 0);
}

function kebabToMdiKey(kebab) {
    return (
        "mdi" +
        splitIconParts(kebab)
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join("")
    );
}

export function normalizeIconNameForLookup(name) {
    if (!name || typeof name !== "string") {
        return "";
    }
    return name.trim().toLowerCase().replace(/_/g, "-");
}

export function resolveMdiKebabIconName(iconName) {
    const normalized = normalizeIconNameForLookup(iconName);
    if (!normalized) {
        return null;
    }
    if (isValidMdiIconName(normalized)) {
        return normalized;
    }
    if (MATERIAL_SYMBOL_ALIASES[normalized]) {
        return MATERIAL_SYMBOL_ALIASES[normalized];
    }
    const withoutNumericSuffix = normalized.replace(/-\d+$/, "");
    if (withoutNumericSuffix !== normalized && isValidMdiIconName(withoutNumericSuffix)) {
        return withoutNumericSuffix;
    }
    return null;
}

export function resolveMdiIconKey(iconName) {
    if (!iconName) {
        return "mdiAccountOutline";
    }
    if (iconName.startsWith("mdi") && /[A-Z]/.test(iconName)) {
        const aliasKey = MDI_KEY_ALIASES[iconName] || iconName;
        return mdiKeyExists(aliasKey) ? aliasKey : "mdiAccountOutline";
    }
    const resolvedKebab = resolveMdiKebabIconName(iconName);
    const lookupName = resolvedKebab || normalizeIconNameForLookup(iconName);
    const mdiKey = kebabToMdiKey(lookupName);
    const aliasKey = MDI_KEY_ALIASES[mdiKey] || mdiKey;
    return mdiKeyExists(aliasKey) ? aliasKey : "mdiAccountOutline";
}

const FALLBACK_ICON_PATH = MDI_USED_PATHS["mdiHelpCircleOutline"] || MDI_USED_PATHS["mdiProgressQuestion"] || "";

export function getMdiIconPath(iconName) {
    const key = resolveMdiIconKey(iconName);
    const path = MDI_USED_PATHS[key] || fullMdi?.[key];
    if (path) {
        return path;
    }
    if (!fullMdi) {
        void ensureFullMdi();
    }
    return fullMdi ? fullMdi.mdiHelpCircleOutline || fullMdi.mdiProgressQuestion || "" : FALLBACK_ICON_PATH;
}
