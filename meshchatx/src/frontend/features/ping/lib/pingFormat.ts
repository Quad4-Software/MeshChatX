// SPDX-License-Identifier: 0BSD

export type PingResult = {
    rtt: number;
    hops_there: number;
    hops_back: number;
    rssi?: number | null;
    snr?: number | null;
    quality?: number | null;
    receiving_interface: string;
};

export type PingSuccessSummary = {
    duration: string;
    hopsThere: number;
    hopsBack: number;
    rssi?: number | null;
    snr?: number | null;
    quality?: number | null;
    via: string;
};

export function isValidPingDestinationHash(hash: string | null | undefined): boolean {
    return hash != null && String(hash).length === 32;
}

export function isValidPingTimeout(timeout: unknown): boolean {
    const n = Number(timeout);
    return Number.isFinite(n) && n >= 1 && n <= 600;
}

export function formatPingSuccess(pingResult: PingResult, seq: number): { line: string; summary: PingSuccessSummary } {
    const rttMilliseconds = (pingResult.rtt * 1000).toFixed(3);
    const rttDurationString = `${rttMilliseconds}ms`;
    const info = [
        `seq=${seq}`,
        `duration=${rttDurationString}`,
        `hops_there=${pingResult.hops_there}`,
        `hops_back=${pingResult.hops_back}`,
    ];
    if (pingResult.rssi != null) {
        info.push(`rssi=${pingResult.rssi}dBm`);
    }
    if (pingResult.snr != null) {
        info.push(`snr=${pingResult.snr}dB`);
    }
    if (pingResult.quality != null) {
        info.push(`quality=${pingResult.quality}%`);
    }
    info.push(`via=${pingResult.receiving_interface}`);
    return {
        line: info.join(" "),
        summary: {
            duration: rttDurationString,
            hopsThere: pingResult.hops_there,
            hopsBack: pingResult.hops_back,
            rssi: pingResult.rssi,
            snr: pingResult.snr,
            quality: pingResult.quality,
            via: pingResult.receiving_interface,
        },
    };
}
