// SPDX-License-Identifier: 0BSD

export type ProbeReceptionStats = {
    rssi?: number | null;
    snr?: number | null;
    quality?: number | null;
};

export type ProbeResultItem = {
    probe_number: number;
    size: number;
    destination: string;
    via?: string;
    interface?: string;
    status: "delivered" | "timeout" | "failed" | string;
    hops?: number;
    rtt?: number;
    rtt_string?: string;
    reception_stats?: ProbeReceptionStats | null;
};

export type ProbeSummary = {
    sent: number;
    delivered: number;
    timeouts: number;
    failed: number;
};

export type ProbeRequestPayload = {
    destination_hash: string;
    full_name: string;
    size: number;
    probes: number;
    wait: number;
};

export type ProbeApiResponse = {
    results?: ProbeResultItem[];
    sent?: number;
    delivered?: number;
    timeouts?: number;
    failed?: number;
    message?: string;
};
