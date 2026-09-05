// SPDX-License-Identifier: 0BSD

import type { Network } from "vis-network";
import type { DataSet } from "vis-data";
import { computeLodUpdates, lodLevelFromScale } from "../../../js/networkVisualiserPerf.js";
import { resolveVisualiserIsDark } from "./visualiserPrefs.js";

export function handleVisualiserLODUpdate(options: {
    network: Network | null;
    nodes: DataSet<any>;
    currentLOD: string;
    onHighLOD: () => void;
}): string {
    const { network, nodes, currentLOD, onHighLOD } = options;
    if (!network || typeof network.getScale !== "function") return currentLOD;
    const scale = network.getScale();
    const newLOD = lodLevelFromScale(scale);
    if (currentLOD === newLOD) return currentLOD;

    const isDarkMode = resolveVisualiserIsDark();
    const updates = computeLodUpdates(nodes.get(), newLOD, isDarkMode);
    if (updates.length > 0) {
        nodes.update(updates);
    }
    if (newLOD === "high") {
        onHighLOD();
    }
    return newLOD;
}
