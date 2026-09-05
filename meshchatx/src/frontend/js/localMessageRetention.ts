const UNIT_DAYS = "days";
const UNIT_MONTHS = "months";

const MAX_DAYS = 10_000;
const MAX_MONTHS = 120;

/**
 * @param {unknown} value
 * @param {unknown} unit
 * @returns {{ value: number, unit: string }}
 */
export function normalizeRetentionValue(value, unit) {
    const u = String(unit) === UNIT_MONTHS ? UNIT_MONTHS : UNIT_DAYS;
    const cap = u === UNIT_MONTHS ? MAX_MONTHS : MAX_DAYS;
    const n = Number(value);
    const v = Number.isFinite(n) ? Math.trunc(n) : 1;
    return { value: Math.min(Math.max(1, v), cap), unit: u };
}

export { MAX_DAYS as MAX_RETENTION_DAYS, MAX_MONTHS as MAX_RETENTION_MONTHS, UNIT_DAYS, UNIT_MONTHS };
