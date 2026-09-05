// SPDX-License-Identifier: 0BSD

import type { DataSet } from "vis-data";
import { createIconImage } from "./visualiserIconUtils.js";
import type { IconQueueEntry } from "./types.js";

export async function processVisualiserIconQueue(options: {
    queue: IconQueueEntry[];
    generation: number;
    getCurrentGeneration: () => number;
    isNodePresent: (nodeId: string) => boolean;
    updateNodesImage: (updates: Array<{ id: string; image: string }>) => void;
    iconCache: Record<string, string>;
    signal: AbortSignal;
}): Promise<void> {
    const { queue, generation, getCurrentGeneration, isNodePresent, updateNodesImage, iconCache, signal } = options;
    const CHUNK_SIZE = 16;
    for (let i = 0; i < queue.length; i += CHUNK_SIZE) {
        if (generation !== getCurrentGeneration() || signal.aborted) {
            return;
        }
        const chunk = queue.slice(i, i + CHUNK_SIZE);
        const updates: Array<{ id: string; image: string }> = [];

        await Promise.all(
            chunk.map(async ({ nodeId, iconName, fg, bg, size }) => {
                if (generation !== getCurrentGeneration() || signal.aborted) {
                    return;
                }
                const image = await createIconImage(
                    iconName,
                    fg || "#ffffff",
                    bg || "#3b82f6",
                    size || 64,
                    iconCache,
                    signal
                );
                if (generation !== getCurrentGeneration() || signal.aborted) {
                    return;
                }
                if (image && isNodePresent(nodeId)) {
                    updates.push({ id: nodeId, image });
                }
            })
        );

        if (generation === getCurrentGeneration() && !signal.aborted && updates.length > 0) {
            updateNodesImage(updates);
        }
        await new Promise((r) => requestAnimationFrame(r));
    }
}

export function createVisualiserIconQueueManager(options: {
    nodes: DataSet<any>;
    iconCache: Record<string, string>;
    getAbortSignal: () => AbortSignal;
    getLOD: () => string;
}) {
    let queue: IconQueueEntry[] = [];
    let generation = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    function reset() {
        generation += 1;
        queue = [];
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    }

    function push(items: any[]) {
        queue.push(
            ...items.map((item) => ({
                ...item,
                generation,
            }))
        );
        schedule();
    }

    function schedule() {
        if (timer) return;
        timer = setTimeout(() => {
            timer = null;
            void process();
        }, 50);
    }

    async function process() {
        if (queue.length === 0 || options.getLOD() === "low") return;
        const gen = generation;
        const queueToProcess = queue;
        queue = [];

        await processVisualiserIconQueue({
            queue: queueToProcess,
            generation: gen,
            getCurrentGeneration: () => generation,
            isNodePresent: (id) => Boolean(options.nodes.get(id)),
            updateNodesImage: (updates) => options.nodes.update(updates),
            iconCache: options.iconCache,
            signal: options.getAbortSignal(),
        });
    }

    function destroy() {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    }

    return {
        reset,
        push,
        schedule,
        process,
        destroy,
        get generation() {
            return generation;
        },
    };
}
