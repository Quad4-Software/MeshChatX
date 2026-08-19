// SPDX-License-Identifier: 0BSD

/**
 * True when a sidebar link named linkName should highlight for currentName.
 * Child route names use a dotted prefix (interfaces.add under interfaces).
 * @param {unknown} linkName
 * @param {unknown} currentName
 * @returns {boolean}
 */
export function navRouteIsActive(linkName, currentName) {
    if (typeof linkName !== "string" || !linkName || typeof currentName !== "string" || !currentName) {
        return false;
    }
    if (linkName === currentName) {
        return true;
    }
    return currentName.startsWith(`${linkName}.`);
}
