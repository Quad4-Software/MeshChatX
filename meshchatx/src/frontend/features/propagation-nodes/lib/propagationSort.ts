// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import type { PropagationNodeItem, PropagationSortBy } from "./types.js";

/**
 * Filter and sort propagation nodes based on search term and sort mode.
 */
export function filterAndSortNodes(
    nodes: PropagationNodeItem[],
    searchTerm: string,
    sortBy: PropagationSortBy,
    preferredHash: string | null | undefined
): PropagationNodeItem[] {
    const search = (searchTerm || "").trim().toLowerCase();
    const filtered = nodes.filter((node) => {
        if (!search) return true;
        const matchesName = (node.operator_display_name || "").toLowerCase().includes(search);
        const matchesHash = (node.destination_hash || "").toLowerCase().includes(search);
        return matchesName || matchesHash;
    });

    const unknownOperator = t("tools.propagation_nodes.unknown_operator");

    const result = [...filtered];
    switch (sortBy) {
        case "name":
            result.sort((a, b) => {
                const nameA = (a.operator_display_name || unknownOperator).toLowerCase();
                const nameB = (b.operator_display_name || unknownOperator).toLowerCase();
                return nameA.localeCompare(nameB);
            });
            break;
        case "name-desc":
            result.sort((a, b) => {
                const nameA = (a.operator_display_name || unknownOperator).toLowerCase();
                const nameB = (b.operator_display_name || unknownOperator).toLowerCase();
                return nameB.localeCompare(nameA);
            });
            break;
        case "recent":
            result.sort((a, b) => {
                const timeA = new Date(a.updated_at || 0).getTime();
                const timeB = new Date(b.updated_at || 0).getTime();
                return timeB - timeA;
            });
            break;
        case "oldest":
            result.sort((a, b) => {
                const timeA = new Date(a.updated_at || 0).getTime();
                const timeB = new Date(b.updated_at || 0).getTime();
                return timeA - timeB;
            });
            break;
        case "preferred":
        default:
            result.sort((a, b) => {
                const aIsPreferred = preferredHash === a.destination_hash;
                const bIsPreferred = preferredHash === b.destination_hash;
                if (aIsPreferred && !bIsPreferred) return -1;
                if (!aIsPreferred && bIsPreferred) return 1;
                if (a.is_local_node && !b.is_local_node) return -1;
                if (!a.is_local_node && b.is_local_node) return 1;
                const timeA = new Date(a.updated_at || 0).getTime();
                const timeB = new Date(b.updated_at || 0).getTime();
                return timeB - timeA;
            });
            break;
    }
    return result;
}
