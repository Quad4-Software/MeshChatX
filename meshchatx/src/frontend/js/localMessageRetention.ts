const UNIT_DAYS = "days";
const UNIT_MONTHS = "months";

const MAX_DAYS = 10_000;
const MAX_MONTHS = 120;

export type RetentionUnit = typeof UNIT_DAYS | typeof UNIT_MONTHS;

export type RetentionValue = {
    value: number;
    unit: RetentionUnit;
};

export function normalizeRetentionValue(value: unknown, unit: unknown): RetentionValue {
    const u: RetentionUnit = String(unit) === UNIT_MONTHS ? UNIT_MONTHS : UNIT_DAYS;
    const cap = u === UNIT_MONTHS ? MAX_MONTHS : MAX_DAYS;
    const n = Number(value);
    const v = Number.isFinite(n) ? Math.trunc(n) : 1;
    return { value: Math.min(Math.max(1, v), cap), unit: u };
}

export { MAX_DAYS as MAX_RETENTION_DAYS, MAX_MONTHS as MAX_RETENTION_MONTHS, UNIT_DAYS, UNIT_MONTHS };
