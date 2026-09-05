// SPDX-License-Identifier: 0BSD

/**
 * Merge backend resource_breakdown with optional Electron private memory.
 * Electron processMemoryInfo values are kilobytes.
 *
 * @param {Array<{name?: string, rss?: number|null, cpu_percent?: number|null}>|null|undefined} breakdown
 * @param {{ private?: number, residentSet?: number }|null|undefined} electronMemory
 * @returns {Array<{name: string, rss: number|null, cpu_percent: number|null}>}
 */
export function mergeResourceBreakdown(breakdown, electronMemory) {
    const rows = Array.isArray(breakdown)
        ? breakdown
              .filter((row) => row && typeof row === "object")
              .map((row) => ({
                  name: String(row.name || "process"),
                  rss: row.rss == null ? null : Number(row.rss),
                  cpu_percent: row.cpu_percent == null ? null : Number(row.cpu_percent),
              }))
        : [];

    if (electronMemory && typeof electronMemory === "object") {
        const kb = Number(electronMemory.private ?? electronMemory.residentSet);
        if (Number.isFinite(kb) && kb > 0) {
            rows.push({
                name: "electron",
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
