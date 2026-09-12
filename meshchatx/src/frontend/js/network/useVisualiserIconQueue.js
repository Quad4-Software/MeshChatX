// @ts-check
// SPDX-License-Identifier: 0BSD

import { ref } from "vue";

import { dedupeIconQueueEntries } from "../networkVisualiserPerf.js";

/**
 * Deferred lxmf custom-icon queue for NetworkVisualiser. Icon bitmaps are
 * rendered off the graph-apply path and painted sequentially with a main
 * thread yield between each item so a burst of custom icons cannot pin the
 * renderer. Entries tagged with a stale generation (a newer
 * processVisualization started while the queue was running) are dropped, as
 * are nodes that no longer exist.
 *
 * Host-injected options keep the composable free of instance state:
 * - options.getAbortSignal() returns the abort signal for the current run
 * - options.getNodes() returns the vis DataSet used on the canvas path
 * - options.getWebglEngine() returns the active WebGL engine or null
 * - options.createIconImage(name, fg, bg, size) renders one icon bitmap; the
 *   host delegates through the instance proxy so per-test overrides on
 *   wrapper.vm.createIconImage still apply
 * - options.yieldToMain() yields to the browser between icons
 */
export function useVisualiserIconQueue(options = {}) {
    const {
        getAbortSignal,
        getNodes,
        getWebglEngine,
        createIconImage,
        yieldToMain = () => new Promise((resolve) => setTimeout(resolve, 0)),
    } = options;

    const iconCache = ref({});
    const iconQueue = ref([]);
    const iconQueueRunning = ref(false);
    const iconQueueGeneration = ref(0);
    const currentLOD = ref("high");

    const isAborted = () => getAbortSignal?.()?.aborted === true;

    function scheduleIconQueue() {
        if (currentLOD.value === "low" || iconQueue.value.length === 0) {
            return;
        }
        if (iconQueueRunning.value) {
            return;
        }
        const run = () => {
            runIconQueue();
        };
        if (typeof requestIdleCallback === "function") {
            requestIdleCallback(run, { timeout: 1500 });
        } else {
            run();
        }
    }

    /*
     * Drains the deferred lxmf custom-icon queue. Runs sequentially with
     * a yield between each icon so painting many icons cannot pin the
     * main thread the way the old inline-await version did. Items tagged
     * with a stale generation (a newer processVisualization started while
     * we were running) are skipped, as are nodes that no longer exist.
     */
    async function runIconQueue() {
        if (iconQueueRunning.value || currentLOD.value === "low") return;
        iconQueueRunning.value = true;
        try {
            const work = dedupeIconQueueEntries(iconQueue.value);
            iconQueue.value = [];
            for (const item of work) {
                if (isAborted()) return;
                if (item.generation !== iconQueueGeneration.value) {
                    continue;
                }
                let url = iconCache.value[item.cacheKey];
                if (!url) {
                    url = await createIconImage?.(item.iconName, item.fg, item.bg, item.size);
                    if (isAborted()) return;
                }
                if (!url) {
                    continue;
                }
                const updates = [];
                for (const nodeId of item.nodeIds) {
                    if (getWebglEngine?.()) {
                        updates.push({ id: nodeId, image: url });
                    } else if (getNodes?.()?.get(nodeId)) {
                        updates.push({ id: nodeId, image: url });
                    }
                }
                if (updates.length > 0) {
                    const webglEngine = getWebglEngine?.();
                    if (webglEngine) {
                        webglEngine.updateNodeImages(updates);
                    } else {
                        getNodes?.()?.update(updates);
                    }
                }
                await yieldToMain();
            }
        } finally {
            iconQueueRunning.value = false;
            if (iconQueue.value.length > 0 && currentLOD.value !== "low") {
                scheduleIconQueue();
            }
        }
    }

    return {
        iconCache,
        iconQueue,
        iconQueueRunning,
        iconQueueGeneration,
        currentLOD,
        scheduleIconQueue,
        runIconQueue,
    };
}
