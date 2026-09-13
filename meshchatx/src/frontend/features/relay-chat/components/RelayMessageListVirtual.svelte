<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Action } from "svelte/action";
    import { useEventListener } from "runed";
    import RelayMessageEntry from "./RelayMessageEntry.svelte";
    import { estimateRelayEntryHeight, findRelayEntryIndexForMessageKey } from "../lib/relayVirtual.js";
    import type { RrcMessage, RrcTimelineEntry } from "../lib/types.js";

    interface Props {
        entries: RrcTimelineEntry[];
        getScrollElement: () => HTMLElement | null | undefined;
        overscan?: number;
        formatDateDividerLabel: (dayKey?: string) => string;
        isPresenceGroupExpanded: (id?: string) => boolean;
        togglePresenceGroup: (id?: string) => void;
        formatPresenceGroupSummary: (entry: RrcTimelineEntry) => string;
        messageKey: (msg?: RrcMessage) => string;
        renderMessageHtml: (text: string) => string;
        onmessagehtmlclick?: (e: MouseEvent) => void;
        onmessagecontextmenu?: (e: MouseEvent, msg: RrcMessage) => void;
    }

    let {
        entries = [],
        getScrollElement,
        overscan = 12,
        formatDateDividerLabel,
        isPresenceGroupExpanded,
        togglePresenceGroup,
        formatPresenceGroupSummary,
        messageKey,
        renderMessageHtml,
        onmessagehtmlclick,
        onmessagecontextmenu,
    }: Props = $props();

    let scrollTop = $state(0);
    let viewportHeight = $state(0);
    let measuredHeights = $state<Record<number, number>>({});

    function entryKey(entry: RrcTimelineEntry, index: number): string {
        if (!entry) return `idx-${index}`;
        if (entry.type === "dateDivider") return `date-${entry.dayKey}-${index}`;
        if (entry.type === "presenceGroup") return `presence-${entry.id}-${index}`;
        const msgK = messageKey(entry.msg);
        return msgK ? `${msgK}-${index}` : `idx-${index}`;
    }

    const layout = $derived.by(() => {
        let cursor = 0;
        const rows = entries.map((entry, index) => {
            const size = measuredHeights[index] || estimateRelayEntryHeight(entry);
            const row = { index, start: cursor, size, key: entryKey(entry, index) };
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

    export function scrollToMessageKey(key: string) {
        const idx = findRelayEntryIndexForMessageKey(entries as any, key, messageKey as any);
        const el = getScrollElement();
        if (idx < 0 || !el) return;
        const top = Math.max(0, rowOffset(idx) - el.clientHeight / 2);
        el.scrollTo({ top, behavior: "smooth" });
    }

    export function scrollToBottom() {
        const el = getScrollElement();
        if (!el || entries.length === 0) return;
        el.scrollTo({ top: layout.totalSize, behavior: "auto" });
    }

    export function getTotalSize() {
        return layout.totalSize;
    }

    function updateViewport(el: HTMLElement) {
        scrollTop = el.scrollTop;
        viewportHeight = el.clientHeight;
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
        const el = getScrollElement();
        if (!el) return;
        updateViewport(el);
        const observer = new ResizeObserver(() => updateViewport(el));
        observer.observe(el);
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
            <RelayMessageEntry
                entry={entries[row.index]}
                {formatDateDividerLabel}
                {isPresenceGroupExpanded}
                {togglePresenceGroup}
                {formatPresenceGroupSummary}
                {messageKey}
                {renderMessageHtml}
                {onmessagehtmlclick}
                {onmessagecontextmenu}
            />
        </div>
    {/each}
</div>
