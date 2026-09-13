// SPDX-License-Identifier: 0BSD

export type TraceNodeType = "local" | "destination" | "hop" | "unknown" | string;

export type TraceNode = {
    type: TraceNodeType;
    hash?: string | null;
    name?: string | null;
    interface?: string | null;
    hops?: number;
    count?: number;
    hop_number?: number;
};

export type PathTraceResult = {
    destination: string;
    hops: number;
    path: TraceNode[];
    interface?: string | null;
    next_hop?: string | null;
    error?: string;
};
