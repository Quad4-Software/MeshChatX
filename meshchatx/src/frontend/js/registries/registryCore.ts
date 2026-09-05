// SPDX-License-Identifier: 0BSD

/**
 * @template T
 * @typedef {Object} Registry
 * @property {(entry: T) => void} register
 * @property {(id: string) => void} unregister
 * @property {(id: string) => T | undefined} get
 * @property {() => T[]} list
 * @property {() => void} clear
 */

/**
 * @template {{ id: string }} T
 * @param {string} name
 * @returns {Registry<T>}
 */
export function createRegistry(name) {
    /** @type {Map<string, T>} */
    const entries = new Map();

    return {
        register(entry) {
            if (!entry?.id) {
                throw new Error(`${name}: entry requires an id`);
            }
            if (entries.has(entry.id)) {
                throw new Error(`${name}: duplicate entry id "${entry.id}"`);
            }
            entries.set(entry.id, entry);
        },
        unregister(id) {
            entries.delete(id);
        },
        get(id) {
            return entries.get(id);
        },
        list() {
            return Array.from(entries.values());
        },
        clear() {
            entries.clear();
        },
    };
}
