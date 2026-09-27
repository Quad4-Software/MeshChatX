// SPDX-License-Identifier: 0BSD

import type { Network } from "vis-network";
import type { DataSet } from "vis-data";
import { computeLodUpdates, declutterLabelBoxes, lodLevelFromScale } from "../../../js/networkVisualiserPerf.js";
import { resolveVisualiserIsDark } from "./visualiserPrefs.js";
import type { PathTableEntry } from "./types.js";

/**
 * Screen-space label allowlist for high LOD: greedy declutter over every
 * labelled node so dense clusters stay readable instead of stacking into a
 * wall of names. me wins, then interfaces/discovered, then direct peers.
 */
export function visibleLabelIds(
    network: Network | null,
    nodes: DataSet<any>,
    pathTable: PathTableEntry[] | null | undefined,
    scale: number
): Set<string> | null {
    if (!network) return null;
    if (typeof network.getPositions !== "function" || typeof (network as any).canvasToDOM !== "function") {
        return null;
    }
    const all = nodes.get();
    if (!all.length) return null;
    const positions = network.getPositions();
    if (!positions) return null;
    const hopsById: Record<string, number> = {};
    for (const entry of pathTable || []) {
        if (entry?.hash && entry.hops != null) hopsById[entry.hash] = entry.hops;
    }
    const items: Array<{ id: string; sx: number; sy: number; w: number; h: number; pri: number }> = [];
    for (const n of all) {
        const label = n?.originalLabel ?? n?.label;
        if (!n?.id || !label) continue;
        const p = positions[n.id];
        if (!p) continue;
        const dom = (network as any).canvasToDOM(p);
        const fontSize = n.id === "me" ? 16 : 11;
        // vis-network scales label font by camera zoom, so the collision
        // boxes must scale too or they under-cover at high zoom and
        // overlapping labels pass the test.
        items.push({
            id: n.id,
            sx: dom.x,
            sy: dom.y + (Number(n.size) || 10) * scale + 4 + fontSize * 0.6 * scale,
            w: String(label).length * fontSize * 0.56 * scale,
            h: fontSize * 1.35 * scale,
            pri:
                n.id === "me"
                    ? 0
                    : n.group === "interface" || n.group === "discovered"
                      ? 2
                      : hopsById[n.id] === 1
                        ? 3
                        : 4,
        });
    }
    items.sort((a, b) => a.pri - b.pri);
    return declutterLabelBoxes(items, 4);
}

export function handleVisualiserLODUpdate(options: {
    network: Network | null;
    nodes: DataSet<any>;
    currentLOD: string;
    pathTable?: PathTableEntry[] | null;
    onHighLOD: () => void;
}): string {
    const { network, nodes, currentLOD, pathTable, onHighLOD } = options;
    if (!network || typeof network.getScale !== "function") return currentLOD;
    const scale = network.getScale();
    const newLOD = lodLevelFromScale(scale);
    const lodChanged = currentLOD !== newLOD;

    // At high zoom, keep only labels that fit without overlapping so dense
    // clusters stay readable. Recomputed on every zoom change, not just band
    // crossings.
    const labelAllow = newLOD === "high" ? visibleLabelIds(network, nodes, pathTable, scale) : null;
    if (!lodChanged && !labelAllow) return currentLOD;

    // Only mutate nodes whose LOD props actually change (avoids O(N) DataSet
    // churn + full redraw when zooming across thresholds).
    const isDarkMode = resolveVisualiserIsDark();
    const updates = computeLodUpdates(nodes.get(), newLOD, isDarkMode, labelAllow);
    if (updates.length > 0) {
        nodes.update(updates);
    }
    if (newLOD === "high") {
        onHighLOD();
    }
    return newLOD;
}
