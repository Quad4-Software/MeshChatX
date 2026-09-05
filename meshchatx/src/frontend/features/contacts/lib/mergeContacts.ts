// SPDX-License-Identifier: 0BSD

/**
 * Merge contacts that share the same display name so LXMF and LXST hashes show on one row.
 */
export type ContactRecord = Record<string, unknown> & {
    name?: string;
    lxmf_address?: string;
    lxst_address?: string;
    remote_destination_hash?: string;
    remote_telephony_hash?: string;
    remote_identity_hash?: string;
};

export function mergeContactsByName(contacts: ContactRecord[]): ContactRecord[] {
    const map = new Map<string, ContactRecord>();
    for (const c of contacts) {
        const key = String(c.name || "").toLowerCase();
        if (!map.has(key)) {
            map.set(key, { ...c });
        } else {
            const existing = map.get(key)!;
            existing.lxmf_address = existing.lxmf_address || c.lxmf_address;
            existing.lxst_address = existing.lxst_address || c.lxst_address;
            existing.remote_destination_hash = existing.remote_destination_hash || c.remote_destination_hash;
            existing.remote_telephony_hash = existing.remote_telephony_hash || c.remote_telephony_hash;
            existing.remote_identity_hash = existing.remote_identity_hash || c.remote_identity_hash;
        }
    }
    return Array.from(map.values());
}
