<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Action } from "svelte/action";
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
