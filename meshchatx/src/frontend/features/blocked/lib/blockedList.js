// SPDX-License-Identifier: 0BSD

/**
 * Pure helpers for the blocked / banished identities list.
 */

/**
 * @param {object} identity
 * @returns {string | null}
 */
export function identityBlockedAt(identity) {
    const dates = (identity.blocked_destinations || []).map((dest) => dest.created_at).filter(Boolean);
    if (dates.length === 0) {
        return null;
    }
    return dates.sort().reverse()[0];
}

/**
 * @param {object} a
 * @param {object} b
 * @returns {number}
 */
export function compareBlockedAt(a, b) {
    const atA = identityBlockedAt(a) || "";
    const atB = identityBlockedAt(b) || "";
    if (atA === atB) {
        const nameA = (a.display_name || a.identity_hash).toLowerCase();
        const nameB = (b.display_name || b.identity_hash).toLowerCase();
        return nameA.localeCompare(nameB);
    }
    return atA.localeCompare(atB);
}

/**
 * @param {object[]} identities
 * @param {{ searchQuery?: string, typeFilter?: string, dateSort?: string }} opts
 * @returns {object[]}
 */
export function filterBlockedIdentities(identities, opts = {}) {
    let list = [...identities];
    const query = String(opts.searchQuery || "")
        .trim()
        .toLowerCase();
    if (query) {
        list = list.filter((identity) => {
            if (identity.identity_hash.toLowerCase().includes(query)) return true;
            if ((identity.display_name || "").toLowerCase().includes(query)) return true;
            return (identity.blocked_destinations || []).some((d) => d.destination_hash.toLowerCase().includes(query));
        });
    }

    if (opts.typeFilter === "user") {
        list = list.filter((identity) => !identity.is_node && !identity.is_rns_blackholed);
    } else if (opts.typeFilter === "node") {
        list = list.filter((identity) => identity.is_node);
    } else if (opts.typeFilter === "rns") {
        list = list.filter((identity) => identity.is_rns_blackholed);
    }

    if (opts.dateSort === "name") {
        list.sort((a, b) => {
            const nameA = (a.display_name || a.identity_hash).toLowerCase();
            const nameB = (b.display_name || b.identity_hash).toLowerCase();
            return nameA.localeCompare(nameB);
        });
    } else if (opts.dateSort === "oldest") {
        list.sort((a, b) => compareBlockedAt(a, b));
    } else {
        list.sort((a, b) => compareBlockedAt(b, a));
    }

    return list;
}
