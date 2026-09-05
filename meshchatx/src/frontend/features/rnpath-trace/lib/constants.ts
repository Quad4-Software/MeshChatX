// SPDX-License-Identifier: 0BSD

/** API base path for rnpath trace endpoint */
export const RNPATH_TRACE_API_BASE = "/api/v1/rnpath/trace";

/** Node types in path trace */
export const TRACE_NODE_TYPE = {
    LOCAL: "local",
    DESTINATION: "destination",
    HOP: "hop",
    UNKNOWN: "unknown",
} as const;
