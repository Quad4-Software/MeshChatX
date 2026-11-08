// SPDX-License-Identifier: 0BSD AND MIT

/**
 * Merge backend resource_breakdown with optional desktop-shell private memory.
 * Shell process memory values are kilobytes.
 *
 * @param {Array<{name?: string, rss?: number|null, cpu_percent?: number|null}>|null|undefined} breakdown
 * @param {{ private?: number, residentSet?: number }|null|undefined} shellMemory
 * @returns {Array<{name: string, rss: number|null, cpu_percent: number|null}>}
 */
export function mergeResourceBreakdown(breakdown, shellMemory) {
    const rows = Array.isArray(breakdown)
        ? breakdown
              .filter((row) => row && typeof row === "object")
              .map((row) => ({
                  name: String(row.name || "process"),
                  rss: row.rss == null ? null : Number(row.rss),
                  cpu_percent: row.cpu_percent == null ? null : Number(row.cpu_percent),
              }))
        : [];

    if (shellMemory && typeof shellMemory === "object") {
        const kb = Number(shellMemory.private ?? shellMemory.residentSet);
        if (Number.isFinite(kb) && kb > 0) {
            rows.push({
                name: "desktop",
                rss: Math.round(kb * 1024),
                cpu_percent: null,
            });
        }
    }
    return rows;
}

/**
 * @param {Array<{name: string, rss: number|null, cpu_percent: number|null}>} rows
 * @returns {{name: string, rss: number|null, cpu_percent: number|null}|null}
 */
export function topResourceByRss(rows) {
    if (!Array.isArray(rows) || rows.length === 0) return null;
    const scored = rows.filter((r) => r.rss != null && Number.isFinite(r.rss));
    if (!scored.length) return null;
    return scored.reduce((best, row) => (row.rss > best.rss ? row : best));
}

/**
 * @param {Array<{name: string, rss: number|null, cpu_percent: number|null}>} rows
 * @returns {{name: string, rss: number|null, cpu_percent: number|null}|null}
 */
export function topResourceByCpu(rows) {
    if (!Array.isArray(rows) || rows.length === 0) return null;
    const scored = rows.filter((r) => r.cpu_percent != null && Number.isFinite(r.cpu_percent));
    if (!scored.length) return null;
    return scored.reduce((best, row) => (row.cpu_percent > best.cpu_percent ? row : best));
}
