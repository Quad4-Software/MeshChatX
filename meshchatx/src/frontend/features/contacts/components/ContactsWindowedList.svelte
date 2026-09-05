<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import { SIDEBAR_ROW_ESTIMATE_PX } from "../../../js/sidebarListVirtual.js";

    interface Props {
        items: Array<Record<string, unknown>>;
        getScrollElement: () => HTMLElement | null | undefined;
        itemKey: (item: Record<string, unknown>, index: number) => string;
        rowHeight?: number;
        overscan?: number;
        children: Snippet<[{ item: Record<string, unknown>; index: number }]>;
    }

    let {
        items = [],
        getScrollElement,
        itemKey,
        rowHeight = SIDEBAR_ROW_ESTIMATE_PX,
        overscan = 8,
        children,
    }: Props = $props();

    let scrollTop = $state(0);
    let viewportHeight = $state(0);

    const totalSize = $derived(Math.max(0, items.length * rowHeight));

    const virtualRows = $derived.by(() => {
        if (items.length === 0) {
            return [];
        }
        const start = Math.max(0, scrollTop);
        const end = start + Math.max(viewportHeight, 1);
        const firstVisible = Math.max(0, Math.floor(start / rowHeight) - overscan);
        const lastVisible = Math.min(items.length, Math.ceil(end / rowHeight) + overscan);
        const rows = [];
        for (let index = firstVisible; index < lastVisible; index += 1) {
            rows.push({
                index,
                start: index * rowHeight,
                key: itemKey(items[index], index),
            });
        }
        return rows;
    });

    $effect(() => {
        const el = getScrollElement();
        if (!el) return;
        const updateViewport = () => {
            scrollTop = el.scrollTop;
            viewportHeight = el.clientHeight;
        };
        updateViewport();
        el.addEventListener("scroll", updateViewport, { passive: true });
        const observer = new ResizeObserver(updateViewport);
        observer.observe(el);
        return () => {
            el.removeEventListener("scroll", updateViewport);
            observer.disconnect();
        };
    });
</script>

<div class="relative w-full shrink-0" style:height={`${totalSize}px`}>
    {#each virtualRows as row (row.key)}
        <div
            class="absolute left-0 top-0 w-full box-border [overflow-anchor:none]"
            style:transform={`translateY(${row.start}px)`}
        >
            {@render children({ item: items[row.index], index: row.index })}
        </div>
    {/each}
</div>
