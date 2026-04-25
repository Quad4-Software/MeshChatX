/**
 * RNode carrier frequency as integer Hz for API payloads (Reticulum stores Hz, not MHz decimals).
 */
export function parseRNodeFrequencyHz(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }
    if (typeof value === "number" && Number.isFinite(value)) {
        let f = value;
        if (f <= 0) {
            return Math.round(f);
        }
        if (f >= 1_000_000) {
            return Math.round(f);
        }
        const isInteger = Math.abs(f - Math.round(f)) < 1e-9;
        if (!isInteger || (isInteger && f < 10_000)) {
            f *= 1_000_000;
        }
        return Math.round(f);
    }
    let s = String(value).trim().toLowerCase().replace(/_/g, "");
    let mult = 1;
    const pairs = [
        ["ghz", 1e9],
        ["mhz", 1e6],
        ["khz", 1e3],
        ["hz", 1],
    ];
    for (const [suffix, m] of pairs) {
        if (s.endsWith(suffix)) {
            s = s.slice(0, -suffix.length).trim();
            mult = m;
            break;
        }
    }
    const n = Number(s);
    if (!Number.isFinite(n)) {
        return null;
    }
    let f = n * mult;
    if (f <= 0) {
        return Math.round(f);
    }
    if (f >= 1_000_000) {
        return Math.round(f);
    }
    const isInteger = Math.abs(f - Math.round(f)) < 1e-9;
    if (!isInteger || (isInteger && f < 10_000)) {
        f *= 1_000_000;
    }
    return Math.round(f);
}

/**
 * Coordinates and optional discovery numerics: empty or invalid means "not set" (Reticulum treats omission as optional).
 */
export function numOrNull(value) {
    if (value === null || value === undefined || value === "") return null;
    if (typeof value === "string") {
        const t = value.trim();
        if (t === "") return null;
        const n = Number(t);
        return Number.isFinite(n) ? n : null;
    }
    if (typeof value === "number") {
        return Number.isFinite(value) ? value : null;
    }
    return null;
}
