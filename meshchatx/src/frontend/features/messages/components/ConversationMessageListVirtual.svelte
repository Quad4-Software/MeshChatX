<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Action } from "svelte/action";
    import { useEventListener } from "runed";
    import ConversationMessageEntry, { type MessageDisplayEntry } from "./ConversationMessageEntry.svelte";
    import { estimateGroupHeight, findDisplayGroupIndexForMessageHash } from "../lib/messageListVirtual.js";
    import type { ConversationViewerActions } from "../lib/viewerActions.js";

    let {
        groups,
        getScrollElement,
        actions,
        conversationKey = "",
        overscan = 10,
    }: {
        groups: MessageDisplayEntry[];
        getScrollElement: () => HTMLElement | null | undefined;
        actions: ConversationViewerActions;
        conversationKey?: string;
        overscan?: number;
    } = $props();

    // Measurements are keyed by group key, which is stable across renders but
    // not across conversations. Drop stale entries when the conversation
    // changes and cap the record so long sessions cannot grow it forever.
    const MAX_MEASURED_HEIGHTS = 2000;

    let scrollTop = $state(0);
    let viewportHeight = $state(0);
    let measuredHeights = $state<Record<string, number>>({});
    let lastConversationKey: string | null = null;

    $effect(() => {
        const key = conversationKey;
        if (key !== lastConversationKey) {
            lastConversationKey = key;
            measuredHeights = {};
        }
    });

    function rowHeightKey(group: MessageDisplayEntry, index: number): string {
        return group.key || `${group.type}-${index}`;
    }

    function pruneMeasuredHeights() {
        const keys = Object.keys(measuredHeights);
        if (keys.length <= MAX_MEASURED_HEIGHTS) return;
        const live = new Set(groups.map((group, index) => rowHeightKey(group, index)));
        const next: Record<string, number> = {};
        for (const key of keys) {
            if (live.has(key)) {
                next[key] = measuredHeights[key];
            }
        }
        measuredHeights = next;
    }

    const layout = $derived.by(() => {
        let cursor = 0;
        const rows = groups.map((group, index) => {
            const key = rowHeightKey(group, index);
            const size = measuredHeights[key] || estimateGroupHeight(group);
            const row = { index, start: cursor, size, key };
            cursor += size;
            return row;
        });
        return { rows, totalSize: cursor };
    });

    function visibleRowBounds(rows: { start: number; size: number }[], start: number, end: number) {
        // rows are sorted by start and contiguous, so binary search the window
        let lo = 0;
        let hi = rows.length;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (rows[mid].start + rows[mid].size < start) lo = mid + 1;
            else hi = mid;
        }
        const firstVisible = lo;
        lo = firstVisible;
        hi = rows.length;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (rows[mid].start <= end) lo = mid + 1;
            else hi = mid;
        }
        return { firstVisible, lastVisible: lo };
    }

    const virtualRows = $derived.by(() => {
        const start = Math.max(0, scrollTop);
        const end = start + Math.max(viewportHeight, 1);
        const { firstVisible, lastVisible } = visibleRowBounds(layout.rows, start, end);
        if (lastVisible <= firstVisible) {
            return layout.rows.slice(0, Math.min(layout.rows.length, overscan * 2 + 1));
        }
        const first = Math.max(0, firstVisible - overscan);
        const last = Math.min(layout.rows.length, lastVisible + overscan);
        return layout.rows.slice(first, last);
    });

    const measure: Action<HTMLElement, number> = (node, initialIndex) => {
        let index = initialIndex;
        const update = () => {
            const group = groups[index];
            if (!group) return;
            const key = rowHeightKey(group, index);
            const next = Math.ceil(node.getBoundingClientRect().height);
            if (next > 0 && measuredHeights[key] !== next) {
                measuredHeights[key] = next;
                pruneMeasuredHeights();
            }
        };
        update();
        const observer = new ResizeObserver(update);
        observer.observe(node);
        return {
            update(nextIndex: number) {
                index = nextIndex;
                update();
            },
            destroy: () => observer.disconnect(),
        };
    };

    function rowOffset(index: number) {
        return layout.rows[index]?.start || 0;
    }

    export function scrollToMessageHash(hash: string) {
        const index = findDisplayGroupIndexForMessageHash(groups, hash);
        const element = getScrollElement();
        if (index < 0 || !element) {
            return;
        }
        const top = Math.max(0, rowOffset(index) - element.clientHeight / 2);
        element.scrollTo({ top, behavior: "smooth" });
    }

    export function scrollToBottom() {
        const element = getScrollElement();
        if (!element || groups.length === 0) {
            return;
        }
        element.scrollTo({ top: layout.totalSize, behavior: "auto" });
    }

    export function getTotalSize() {
        return layout.totalSize;
    }

    function updateViewport(element: HTMLElement) {
        scrollTop = element.scrollTop;
        viewportHeight = element.clientHeight;
    }

    useEventListener(
        () => getScrollElement(),
        "scroll",
        (event) => {
            updateViewport(event.currentTarget);
        },
        { passive: true }
    );

    $effect(() => {
        const element = getScrollElement();
        if (!element) {
            return;
        }
        updateViewport(element);
        const observer = new ResizeObserver(() => updateViewport(element));
        observer.observe(element);
        return () => {
            observer.disconnect();
        };
    });
</script>

<div class="relative w-full shrink-0" style:height={`${layout.totalSize}px`}>
    {#each virtualRows as row (row.key)}
        <div
            use:measure={row.index}
            data-index={row.index}
            class="absolute left-0 top-0 w-full box-border px-0 [overflow-anchor:none]"
            style:transform={`translateY(${row.start}px)`}
        >
            <ConversationMessageEntry entry={groups[row.index]} {actions} />
        </div>
    {/each}
</div>
