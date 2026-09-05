// SPDX-License-Identifier: 0BSD

/**
 * Pure helpers for the blocked / banished identities list.
 */

export type BlockedDestination = {
    destination_hash: string;
    created_at?: string;
};

export type BlockedIdentity = {
    identity_hash: string;
    display_name?: string;
    is_node?: boolean;
    is_rns_blackholed?: boolean;
    blocked_destinations?: BlockedDestination[];
};

export type FilterBlockedOpts = {
    searchQuery?: string;
    typeFilter?: string;
    dateSort?: string;
};

export function identityBlockedAt(identity: BlockedIdentity): string | null {
    const dates = (identity.blocked_destinations || []).map((dest) => dest.created_at).filter(Boolean) as string[];
    if (dates.length === 0) {
        return null;
    }
    return dates.sort().reverse()[0];
}

export function compareBlockedAt(a: BlockedIdentity, b: BlockedIdentity): number {
    const atA = identityBlockedAt(a) || "";
    const atB = identityBlockedAt(b) || "";
    if (atA === atB) {
        const nameA = (a.display_name || a.identity_hash).toLowerCase();
        const nameB = (b.display_name || b.identity_hash).toLowerCase();
        return nameA.localeCompare(nameB);
    }
    return atA.localeCompare(atB);
}

export function filterBlockedIdentities(
    identities: BlockedIdentity[],
    opts: FilterBlockedOpts = {}
): BlockedIdentity[] {
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
