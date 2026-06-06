// SPDX-License-Identifier: 0BSD AND MIT

import * as mdi from "@mdi/js";

export const DEFAULT_RRC_HUB_ICON = "forum-outline";

const MDI_KEY_ALIASES = {
    mdiRoute: "mdiRoutes",
    mdiEmailSendOutline: "mdiSendOutline",
};

const MATERIAL_SYMBOL_ALIASES = {
    "bug-report": "bug-outline",
    "smart-toy": "robot-outline",
    "robot-2": "robot-outline",
    "emoji-objects": "lightbulb-on",
};

let cachedIconNames = null;

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

export function buildMdiIconNames() {
    if (cachedIconNames) {
        return cachedIconNames;
    }
    cachedIconNames = Object.keys(mdi).map((mdiIcon) =>
        mdiIcon
            .replace(/^mdi/, "")
            .replace(/([a-z])([A-Z])/g, "$1-$2")
            .toLowerCase()
    );
    return cachedIconNames;
}

export function isValidMdiIconName(name) {
    if (typeof name !== "string" || !name) {
        return false;
    }
    const trimmed = name.trim().toLowerCase();
    if (!isKebabCaseIconName(trimmed)) {
        return false;
    }
    return buildMdiIconNames().includes(trimmed);
}

export function normalizeMdiIconName(name) {
    if (name == null || (typeof name === "string" && !name.trim())) {
        return null;
    }
    const trimmed = String(name).trim().toLowerCase();
    return isValidMdiIconName(trimmed) ? trimmed : null;
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
        return mdi[aliasKey] ? aliasKey : "mdiAccountOutline";
    }
    const resolvedKebab = resolveMdiKebabIconName(iconName);
    const lookupName = resolvedKebab || normalizeIconNameForLookup(iconName);
    const mdiKey = kebabToMdiKey(lookupName);
    const aliasKey = MDI_KEY_ALIASES[mdiKey] || mdiKey;
    return mdi[aliasKey] ? aliasKey : "mdiAccountOutline";
}

export function getMdiIconPath(iconName) {
    const key = resolveMdiIconKey(iconName);
    return mdi[key] || mdi.mdiHelpCircleOutline || mdi.mdiProgressQuestion || "";
}
