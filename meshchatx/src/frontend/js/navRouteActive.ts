// SPDX-License-Identifier: 0BSD

/**
 * True when a sidebar link named linkName should highlight for currentName.
 * Child route names use a dotted prefix (interfaces.add under interfaces).
 */
export function navRouteIsActive(linkName: unknown, currentName: unknown): boolean {
    if (typeof linkName !== "string" || !linkName || typeof currentName !== "string" || !currentName) {
        return false;
    }
    if (linkName === currentName) {
        return true;
    }
    return currentName.startsWith(`${linkName}.`);
}
