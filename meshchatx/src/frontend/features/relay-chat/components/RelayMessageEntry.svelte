<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatTime, nameStyle, displayName } from "../lib/relayFormatters.js";
    import type { RrcMessage, RrcTimelineEntry } from "../lib/types.js";

    interface Props {
        entry: RrcTimelineEntry;
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
        entry,
        formatDateDividerLabel,
        isPresenceGroupExpanded,
        togglePresenceGroup,
        formatPresenceGroupSummary,
        messageKey,
        renderMessageHtml,
        onmessagehtmlclick,
        onmessagecontextmenu,
    }: Props = $props();

    const isSystemLike = $derived.by(() => {
        const kind = entry?.msg?.kind;
        return kind === "system" || kind === "notice" || kind === "error";
    });

    const expanded = $derived.by(() => {
        if (entry?.type !== "presenceGroup") return false;
        return isPresenceGroupExpanded(entry.id);
    });
</script>

{#if entry.type === "dateDivider"}
    <div
        class="flex items-center justify-center gap-3 w-full my-3 shrink-0 px-2 select-none"
        role="separator"
        aria-label={formatDateDividerLabel(entry.dayKey)}
    >
        <span class="h-px w-10 shrink-0 bg-sem-border sm:w-14" aria-hidden="true"></span>
        <span
            class="max-w-[min(100%,18rem)] text-center text-[11px] font-medium leading-snug tracking-wide text-sem-fg-muted"
        >
            {formatDateDividerLabel(entry.dayKey)}
        </span>
        <span class="h-px w-10 shrink-0 bg-sem-border sm:w-14" aria-hidden="true"></span>
    </div>
{:else if entry.type === "presenceGroup"}
    <div class="px-2 py-1">
        <button
            type="button"
            class="mx-auto flex max-w-full items-center gap-1 rounded-md px-2 py-0.5 text-xs italic text-sem-fg-muted transition-colors hover:bg-sem-surface/50 hover:text-sem-fg cursor-pointer"
            aria-expanded={expanded}
            onclick={() => togglePresenceGroup(entry.id)}
        >
            <MaterialDesignIcon
                iconName={expanded ? "chevron-down" : "chevron-right"}
                class="size-3.5 shrink-0 opacity-70"
            />
            <span class="truncate">{formatPresenceGroupSummary(entry)}</span>
        </button>
        {#if expanded && entry.messages}
            <div class="mt-1 space-y-0.5">
                {#each entry.messages as msg, idx (messageKey(msg) || idx)}
                    <div class="py-0.5 text-center text-xs italic text-sem-fg-muted" data-msg-key={messageKey(msg)}>
                        {msg.text}
                    </div>
                {/each}
            </div>
        {/if}
    </div>
{:else if isSystemLike && entry.msg}
    <div
        class="py-0.5 text-center text-xs italic {entry.msg.kind === 'error' ? 'text-sem-danger' : 'text-sem-fg-muted'}"
        data-msg-key={messageKey(entry.msg)}
    >
        {entry.msg.text}
    </div>
{:else if entry.msg && entry.msg.kind === "action"}
    <div
        class="rounded-lg px-2 py-1 text-sm italic {entry.msg.mention ? 'bg-sem-warning/15' : ''}"
        data-msg-key={messageKey(entry.msg)}
    >
        <span class="mr-1 text-xs text-sem-fg-muted">{formatTime(entry.msg.ts)}</span>
        * {displayName(entry.msg)}
        <span
            class="wrap-break-word"
            onclick={(e) => onmessagehtmlclick?.(e)}
            onkeydown={(e) => {
                if (e.key === "Enter") onmessagehtmlclick?.(e as unknown as MouseEvent);
            }}
            role="button"
            tabindex="0"
        >
            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
            {@html renderMessageHtml(entry.msg.text)}
        </span>
    </div>
{:else if entry.msg}
    <div
        class="rounded-lg px-2 py-1 text-sm {entry.msg.mention
            ? 'bg-sem-warning/15'
            : 'hover:bg-sem-surface/40 dark:hover:bg-sem-surface/20'}"
        data-msg-key={messageKey(entry.msg)}
        oncontextmenu={(e) => onmessagecontextmenu?.(e, entry.msg!)}
        role="article"
    >
        <span class="mr-1.5 text-xs text-sem-fg-muted">{formatTime(entry.msg.ts)}</span>
        <span class="mr-1.5 font-semibold" style={nameStyle(entry.msg)}>{displayName(entry.msg)}:</span>
        <span
            class="whitespace-pre-wrap wrap-break-word"
            onclick={(e) => onmessagehtmlclick?.(e)}
            onkeydown={(e) => {
                if (e.key === "Enter") onmessagehtmlclick?.(e as unknown as MouseEvent);
            }}
            role="button"
            tabindex="0"
        >
            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
            {@html renderMessageHtml(entry.msg.text)}
        </span>
    </div>
{/if}
