// SPDX-License-Identifier: 0BSD

export type ResourceBreakdownRow = {
    name: string;
    rss: number | null;
    cpu_percent: number | null;
};

export type ResourceBreakdownInputRow = {
    name?: string;
    rss?: number | null;
    cpu_percent?: number | null;
};

export type ElectronMemoryInfo = {
    private?: number;
    residentSet?: number;
};

/**
 * Merge backend resource_breakdown with optional Electron private memory.
 * Electron processMemoryInfo values are kilobytes.
 */
export function mergeResourceBreakdown(
    breakdown: ResourceBreakdownInputRow[] | null | undefined,
    electronMemory: ElectronMemoryInfo | Record<string, unknown> | null | undefined | unknown
): ResourceBreakdownRow[] {
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
        const mem = electronMemory as ElectronMemoryInfo;
        const kb = Number(mem.private ?? mem.residentSet);
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

export function topResourceByRss(rows: ResourceBreakdownRow[]): ResourceBreakdownRow | null {
    if (!Array.isArray(rows) || rows.length === 0) return null;
    const scored = rows.filter((r) => r.rss != null && Number.isFinite(r.rss));
    if (!scored.length) return null;
    return scored.reduce((best, row) => ((row.rss as number) > (best.rss as number) ? row : best));
}

export function topResourceByCpu(rows: ResourceBreakdownRow[]): ResourceBreakdownRow | null {
    if (!Array.isArray(rows) || rows.length === 0) return null;
    const scored = rows.filter((r) => r.cpu_percent != null && Number.isFinite(r.cpu_percent));
    if (!scored.length) return null;
    return scored.reduce((best, row) => ((row.cpu_percent as number) > (best.cpu_percent as number) ? row : best));
}
