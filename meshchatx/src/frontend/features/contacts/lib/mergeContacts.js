// SPDX-License-Identifier: 0BSD

/**
 * Merge contacts that share the same display name so LXMF and LXST hashes show on one row.
 * @param {Array<Record<string, unknown>>} contacts
 * @returns {Array<Record<string, unknown>>}
 */
export function mergeContactsByName(contacts) {
    const map = new Map();
    for (const c of contacts) {
        const key = String(c.name || "").toLowerCase();
        if (!map.has(key)) {
            map.set(key, { ...c });
        } else {
            const existing = map.get(key);
            existing.lxmf_address = existing.lxmf_address || c.lxmf_address;
            existing.lxst_address = existing.lxst_address || c.lxst_address;
            existing.remote_destination_hash = existing.remote_destination_hash || c.remote_destination_hash;
            existing.remote_telephony_hash = existing.remote_telephony_hash || c.remote_telephony_hash;
            existing.remote_identity_hash = existing.remote_identity_hash || c.remote_identity_hash;
        }
    }
    return Array.from(map.values());
}
