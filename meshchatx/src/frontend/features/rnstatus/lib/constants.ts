// SPDX-License-Identifier: 0BSD

export interface SortOption {
    value: string;
    labelKey: string;
}

export const SORT_OPTIONS: readonly SortOption[] = [
    { value: "", labelKey: "rnstatus.none" },
    { value: "bitrate", labelKey: "rnstatus.bitrate" },
    { value: "rx", labelKey: "rnstatus.rx_bytes" },
    { value: "tx", labelKey: "rnstatus.tx_bytes" },
    { value: "traffic", labelKey: "rnstatus.total_traffic" },
    { value: "announces", labelKey: "rnstatus.announces" },
    { value: "prx", labelKey: "rnstatus.path_requests" },
    { value: "held", labelKey: "rnstatus.held_announces" },
    { value: "gravity", labelKey: "rnstatus.gravity" },
] as const;

export const DEFAULT_REMOTE_TIMEOUT = 15;

export const QUEUE_LABEL_KEYS: Record<string, string> = {
    total: "rnstatus.queue_total",
    data: "rnstatus.queue_data",
    announce: "rnstatus.queue_announce",
    path_request: "rnstatus.queue_path_request",
    ingress_limiter: "rnstatus.queue_ingress_limiter",
};
