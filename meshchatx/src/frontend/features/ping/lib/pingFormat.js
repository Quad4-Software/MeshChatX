// SPDX-License-Identifier: 0BSD

/**
 * @param {string | null | undefined} hash
 * @returns {boolean}
 */
export function isValidPingDestinationHash(hash) {
    return hash != null && String(hash).length === 32;
}

/**
 * @param {unknown} timeout
 * @returns {boolean}
 */
export function isValidPingTimeout(timeout) {
    const n = Number(timeout);
    return Number.isFinite(n) && n >= 1 && n <= 600;
}

/**
 * @param {object} pingResult
 * @param {number} seq
 * @returns {{ line: string, summary: object }}
 */
export function formatPingSuccess(pingResult, seq) {
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
