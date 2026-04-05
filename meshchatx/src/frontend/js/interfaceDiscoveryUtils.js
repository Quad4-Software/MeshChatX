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
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}
