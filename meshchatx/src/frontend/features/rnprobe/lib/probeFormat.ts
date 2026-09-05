// SPDX-License-Identifier: 0BSD

import { isDestinationHash } from "../../../js/meshValidate.js";
import type { ProbeApiResponse, ProbeResultItem, ProbeSummary } from "./types.js";

/**
 * Validate destination hash for rnprobe
 */
export function isValidProbeDestinationHash(hash: unknown): boolean {
    return isDestinationHash(hash);
}

/**
 * Validate full destination name
 */
export function isValidProbeFullName(fullName: unknown): boolean {
    if (typeof fullName !== "string") {
        return false;
    }
    return fullName.trim().length > 0;
}

/**
 * Parse probe summary from api response payload
 */
export function parseProbeSummary(response: ProbeApiResponse): ProbeSummary {
    return {
        sent: Number(response.sent) || 0,
        delivered: Number(response.delivered) || 0,
        timeouts: Number(response.timeouts) || 0,
        failed: Number(response.failed) || 0,
    };
}

/**
 * Determine result item status category
 */
export function isProbeDelivered(item: ProbeResultItem): boolean {
    return item.status === "delivered";
}

export function isProbeTimeout(item: ProbeResultItem): boolean {
    return item.status === "timeout";
}
