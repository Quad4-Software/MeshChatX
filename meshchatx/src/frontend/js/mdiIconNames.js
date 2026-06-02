// SPDX-License-Identifier: 0BSD AND MIT

import * as mdi from "@mdi/js";

export const DEFAULT_RRC_HUB_ICON = "forum-outline";

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
