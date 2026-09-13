// SPDX-License-Identifier: 0BSD

import { isDestinationHash } from "../../../js/meshValidate.js";
import type { TraceNode } from "./types.js";

/**
 * Validate destination hash for path trace
 */
export function isValidTraceHash(hash: unknown): boolean {
    return isDestinationHash(hash);
}

/**
 * Truncate hash for compact visual display
 */
export function formatTraceHash(hash?: string | null): string {
    if (!hash) {
        return "";
    }
    return `${hash.substring(0, 8)}...`;
}

/**
 * CSS classes for trace node icon container
 */
export function getNodeClass(node: TraceNode): string {
    if (node.type === "local") return "bg-blue-600 text-white";
    if (node.type === "destination") return "bg-emerald-600 text-white";
    if (node.type === "unknown") {
        return "bg-sem-surface-muted text-gray-400 dark:text-gray-600 border-2 border-dashed border-sem-border shadow-none";
    }
    return "bg-indigo-600 text-white";
}

/**
 * Icon name for trace node
 */
export function getNodeIcon(node: TraceNode): string {
    if (node.type === "local") return "home";
    if (node.type === "destination") return "flag-variant";
    if (node.type === "unknown") return "dots-horizontal";
    return "router-wireless";
}

/**
 * Check if node is unknown hop type
 */
export function isUnknownTraceNode(node?: TraceNode | null): boolean {
    return node?.type === "unknown";
}
