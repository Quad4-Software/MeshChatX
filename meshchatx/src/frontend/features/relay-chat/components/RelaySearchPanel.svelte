<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SearchInput from "../../../ui/svelte/SearchInput.svelte";
    import { t } from "../../../js/i18n.js";
    import type { RrcMessage } from "../lib/types.js";

    interface Props {
        searchTerm?: string;
        results?: RrcMessage[];
        messageKey?: (msg: RrcMessage) => string;
        displayName?: (msg: RrcMessage) => string;
        nameStyle?: (msg: RrcMessage) => string;
        formatTime?: (ts: number | string | null | undefined) => string;
        onclose?: () => void;
        onselectmessage?: (msg: RrcMessage) => void;
    }

    let {
        searchTerm = $bindable(""),
        results = [],
        messageKey = (m: RrcMessage) => String(m?.seq ?? m?.ts ?? ""),
        displayName = (m: RrcMessage) => m?.nick || "",
        nameStyle = () => "",
        formatTime = (ts) => String(ts ?? ""),
        onclose,
        onselectmessage,
    }: Props = $props();
</script>

<div
    class="absolute inset-y-0 right-0 z-40 flex w-80 max-w-[min(20rem,100%)] min-h-0 flex-col border-l border-sem-border bg-sem-canvas shadow-xl text-sem-fg md:static md:z-auto md:max-w-none md:w-80 md:shadow-none"
>
    <div class="flex shrink-0 items-center justify-between gap-2 border-b border-sem-border px-3 py-2.5">
        <div class="flex items-center gap-1.5 font-semibold">
            <MaterialDesignIcon iconName="magnify" class="size-4 text-sem-accent" />
            {t("relay_chat.search_messages")}
        </div>
        <button
            type="button"
            class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 cursor-pointer"
            title={t("common.close")}
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-4" />
        </button>
    </div>
    <div class="shrink-0 border-b border-sem-border p-2">
        <SearchInput bind:value={searchTerm} compact placeholder={t("relay_chat.search_messages_placeholder")} />
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
        {#if !searchTerm.trim()}
            <div class="flex flex-col items-center gap-2 px-3 py-8 text-center text-xs text-sem-fg-muted">
                <MaterialDesignIcon iconName="magnify" class="size-8 opacity-40" />
                <div class="font-medium text-sem-fg-secondary">{t("relay_chat.search_empty_hint")}</div>
                <div class="leading-relaxed">{t("relay_chat.search_syntax_hint")}</div>
            </div>
        {:else if results.length === 0}
            <div class="px-2 py-4 text-center text-xs text-sem-fg-muted">
                {t("relay_chat.search_no_results")}
            </div>
        {:else}
            {#each results as msg ("search-" + messageKey(msg))}
                <button
                    type="button"
                    class="w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-sem-surface/60 cursor-pointer"
                    onclick={() => onselectmessage?.(msg)}
                >
                    <span class="font-semibold" style={nameStyle(msg)}>{displayName(msg)}</span>
                    <span class="ml-1 text-sem-fg-muted">{formatTime(msg.ts)}</span>
                    <div class="truncate text-sem-fg-secondary">{msg.text}</div>
                </button>
            {/each}
        {/if}
    </div>
</div>
