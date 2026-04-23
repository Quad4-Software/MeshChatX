/**
 * Builds SVG paths and layout metadata for a telemetry battery trend chart.
 * Uses a wide viewBox so preserveAspectRatio "meet" fills typical modal widths
 * without leaving a short square plot.
 */

export const BATTERY_CHART_VIEWBOX = { w: 100, h: 46 };

export const BATTERY_CHART_BOUNDS = {
    PL: 10,
    PR: 99,
    PT: 5,
    PB: 38,
};

const { PL, PR, PT, PB } = BATTERY_CHART_BOUNDS;
const VB = BATTERY_CHART_VIEWBOX;

/**
 * @param {number} v
 * @returns {number}
 */
export function clampBatteryPercent(v) {
    const n = Number(v);
    if (Number.isNaN(n)) return 0;
    return Math.min(100, Math.max(0, n));
}

/**
 * @param {{ x: number; y: number }[]} history ascending by x
 * @returns {{ x: number; y: number }[]}
 */
function plotPoints(history) {
    if (history.length === 0) return [];
    const minX = history[0].x;
    const maxX = history[history.length - 1].x;
    const rangeX = maxX - minX || 1;
    return history.map((p) => ({
        x: PL + ((p.x - minX) / rangeX) * (PR - PL),
        y: PT + (1 - clampBatteryPercent(p.y) / 100) * (PB - PT),
    }));
}

/**
 * Smooth cubic path through points (Catmull-Rom style control points).
 * @param {{ x: number; y: number }[]} pts
 * @returns {string}
 */
function smoothLinePath(pts) {
    if (pts.length === 0) return "";
    if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
        const p0 = i > 0 ? pts[i - 1] : pts[0];
        const p1 = pts[i];
        const p2 = pts[i + 1];
        const p3 = i + 2 < pts.length ? pts[i + 2] : p2;
        const cp1x = p1.x + (p2.x - p0.x) / 6;
        const cp1y = p1.y + (p2.y - p0.y) / 6;
        const cp2x = p2.x - (p3.x - p1.x) / 6;
        const cp2y = p2.y - (p3.y - p1.y) / 6;
        d += ` C ${cp1x} ${cp1y} ${cp2x} ${cp2y} ${p2.x} ${p2.y}`;
    }
    return d;
}

/**
 * @param {{ x: number; y: number }[]} history
 * @param {string} idSuffix alphanumeric fragment for SVG defs ids
 * @returns {null | {
 *   linePath: string;
 *   areaPath: string;
 *   gridLines: { y1: number; y2: number; label: string }[];
 *   first: { x: number; y: number };
 *   last: { x: number; y: number };
 *   plotBottom: number;
 *   gradientId: string;
 *   strokeGradientId: string;
 *   layout: { PL: number; PR: number; PT: number; PB: number; plotBottom: number; minX: number; maxX: number };
 *   viewBox: string;
 * }}
 */
export function buildTelemetryBatteryChartSpec(history, idSuffix = "chart") {
    const safe = String(idSuffix).replace(/[^a-zA-Z0-9_-]/g, "") || "chart";
    if (history.length < 2) return null;

    const minX = history[0].x;
    const maxX = history[history.length - 1].x;

    const pts = plotPoints(history);
    const linePath = smoothLinePath(pts);
    const first = pts[0];
    const last = pts[pts.length - 1];
    const plotBottom = Math.min(PB + 5, VB.h - 1);
    const areaPath = `${linePath} L ${last.x} ${plotBottom} L ${first.x} ${plotBottom} Z`;

    const gridLines = [100, 75, 50, 25, 0].map((pct) => {
        const y = PT + (1 - pct / 100) * (PB - PT);
        return { y1: y, y2: y, label: `${pct}` };
    });

    return {
        linePath,
        areaPath,
        gridLines,
        first,
        last,
        plotBottom,
        gradientId: `tb-fill-${safe}`,
        strokeGradientId: `tb-stroke-${safe}`,
        layout: { PL, PR, PT, PB, plotBottom, minX, maxX },
        viewBox: `0 0 ${VB.w} ${VB.h}`,
    };
}

/**
 * Linear interpolation of charge_percent between samples (by timestamp).
 * @param {{ x: number; y: number }[]} history ascending by x
 * @param {number} ts unix seconds
 * @returns {{ y: number; x: number }}
 */
export function interpolateBatteryByTime(history, ts) {
    if (!history.length) return { y: 0, x: ts };
    if (history.length === 1) return { y: clampBatteryPercent(history[0].y), x: history[0].x };
    if (ts <= history[0].x) return { y: clampBatteryPercent(history[0].y), x: history[0].x };
    const hiLast = history[history.length - 1];
    if (ts >= hiLast.x) return { y: clampBatteryPercent(hiLast.y), x: hiLast.x };

    let lo = 0;
    let hi = history.length - 1;
    while (hi - lo > 1) {
        const mid = (lo + hi) >> 1;
        if (history[mid].x <= ts) lo = mid;
        else hi = mid;
    }
    const a = history[lo];
    const b = history[hi];
    const span = b.x - a.x || 1;
    const u = (ts - a.x) / span;
    return { y: clampBatteryPercent(a.y + u * (b.y - a.y)), x: ts };
}

/**
 * @param {object[]} telemetryChatItems lxmf chat items (telemetry-only ok)
 * @returns {{ x: number; y: number }[]}
 */
export function batteryHistoryFromTelemetryItems(telemetryChatItems) {
    return telemetryChatItems
        .filter((item) => item.lxmf_message?.fields?.telemetry?.battery)
        .map((item) => ({
            x: item.lxmf_message.timestamp,
            y: item.lxmf_message.fields.telemetry.battery.charge_percent,
        }))
        .sort((a, b) => a.x - b.x);
}
