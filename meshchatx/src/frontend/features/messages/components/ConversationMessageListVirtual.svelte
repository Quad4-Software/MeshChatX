<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Action } from "svelte/action";
    import ConversationMessageEntry, { type MessageDisplayEntry } from "./ConversationMessageEntry.svelte";
    import { estimateGroupHeight, findDisplayGroupIndexForMessageHash } from "../lib/messageListVirtual.js";
    import type { ConversationViewerActions } from "../lib/viewerActions.js";

    let {
        groups,
        getScrollElement,
        actions,
        overscan = 10,
    }: {
        groups: MessageDisplayEntry[];
        getScrollElement: () => HTMLElement | null | undefined;
        actions: ConversationViewerActions;
        overscan?: number;
    } = $props();

    let scrollTop = $state(0);
    let viewportHeight = $state(0);
    let measuredHeights = $state<Record<number, number>>({});

    const layout = $derived.by(() => {
        let cursor = 0;
        const rows = groups.map((group, index) => {
            const size = measuredHeights[index] || estimateGroupHeight(group);
            const row = { index, start: cursor, size, key: group.key || `${group.type}-${index}` };
            cursor += size;
            return row;
        });
        return { rows, totalSize: cursor };
    });

    const virtualRows = $derived.by(() => {
        const start = Math.max(0, scrollTop);
        const end = start + Math.max(viewportHeight, 1);
        const visible = layout.rows.filter((row) => row.start + row.size >= start && row.start <= end);
        if (visible.length === 0) {
            return layout.rows.slice(0, Math.min(layout.rows.length, overscan * 2 + 1));
        }
        const first = Math.max(0, visible[0].index - overscan);
        const last = Math.min(layout.rows.length, visible[visible.length - 1].index + overscan + 1);
        return layout.rows.slice(first, last);
    });

    const measure: Action<HTMLElement, number> = (node, index) => {
        const update = () => {
            const next = Math.ceil(node.getBoundingClientRect().height);
            if (next > 0 && measuredHeights[index] !== next) {
                measuredHeights[index] = next;
            }
        };
        update();
        const observer = new ResizeObserver(update);
        observer.observe(node);
        return {
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

    $effect(() => {
        const element = getScrollElement();
        if (!element) {
            return;
        }
        const updateViewport = () => {
            scrollTop = element.scrollTop;
            viewportHeight = element.clientHeight;
        };
        updateViewport();
        element.addEventListener("scroll", updateViewport, { passive: true });
        const observer = new ResizeObserver(updateViewport);
        observer.observe(element);
        return () => {
            element.removeEventListener("scroll", updateViewport);
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
