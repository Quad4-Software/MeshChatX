// SPDX-License-Identifier: 0BSD

export interface Registry<T> {
    register: (entry: T) => void;
    unregister: (id: string) => void;
    get: (id: string) => T | undefined;
    list: () => T[];
    clear: () => void;
}

export function createRegistry<
    T extends { id: string; [key: string]: any } = {
        id: string;
        path?: string;
        keywords?: string[];
        component?: any;
        [key: string]: any;
    },
>(name: string): Registry<T> {
    const entries = new Map<string, T>();

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
