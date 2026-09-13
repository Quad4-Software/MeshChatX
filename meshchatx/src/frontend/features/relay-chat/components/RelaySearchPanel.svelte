<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { t } from "../../../js/i18n.js";
    import { filterRelayMessages } from "../../../js/relayMessageSearch.js";
    import { formatTime, displayName } from "../lib/relayFormatters.js";
    import type { RrcMessage } from "../lib/types.js";

    interface Props {
        messages: RrcMessage[];
        onclose?: () => void;
        onselectmessage?: (msg: RrcMessage) => void;
    }

    let { messages = [], onclose, onselectmessage }: Props = $props();

    let searchTerm = $state("");

    const matchedMessages = $derived.by(() => {
        if (!searchTerm.trim()) return [];
        return filterRelayMessages(messages, searchTerm, displayName);
    });
</script>

<div
    class="absolute inset-y-0 right-0 z-40 flex w-80 max-w-[min(20rem,100%)] min-h-0 flex-col border-l border-sem-border bg-sem-canvas shadow-xl text-sem-fg md:static md:z-auto md:max-w-none md:w-80 md:shadow-none"
>
    <div class="flex items-center justify-between px-3 py-2 border-b border-sem-border">
        <div class="flex items-center gap-1.5 font-semibold text-sm">
            <MaterialDesignIcon iconName="magnify" class="size-4 text-sem-fg-muted" />
            <span>{t("relay_chat.search_messages")}</span>
        </div>
        <IconButton
            class="size-7 text-sem-fg-muted hover:text-sem-fg"
            title={t("common.close")}
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-4" />
        </IconButton>
    </div>

    <div class="p-2 border-b border-sem-border">
        <input
            type="text"
            bind:value={searchTerm}
            placeholder={t("relay_chat.search_placeholder")}
            class="w-full px-2.5 py-1.5 text-xs bg-sem-canvas border border-sem-border rounded-md text-sem-fg focus:outline-hidden focus:border-sem-accent"
        />
        {#if searchTerm.trim()}
            <div class="mt-1 text-[11px] text-sem-fg-muted">
                {t("relay_chat.search_results_count", { count: matchedMessages.length })}
            </div>
        {/if}
    </div>

    <div class="flex-1 overflow-y-auto p-2 space-y-1">
        {#if !searchTerm.trim()}
            <div class="p-4 text-center text-xs text-sem-fg-muted">
                {t("relay_chat.type_to_search")}
            </div>
        {:else if matchedMessages.length === 0}
            <div class="p-4 text-center text-xs text-sem-fg-muted">
                {t("relay_chat.no_search_results")}
            </div>
        {:else}
            {#each matchedMessages as msg (msg.seq || msg.ts)}
                <button
                    type="button"
                    class="w-full text-left p-2 rounded-lg bg-sem-canvas border border-sem-border hover:border-sem-accent transition-colors cursor-pointer"
                    onclick={() => onselectmessage?.(msg)}
                >
                    <div class="flex items-center justify-between text-[11px] text-sem-fg-muted mb-0.5">
                        <span class="font-semibold">{displayName(msg)}</span>
                        <span>{formatTime(msg.ts)}</span>
                    </div>
                    <div class="text-xs text-sem-fg line-clamp-2 break-words">
                        {msg.text}
                    </div>
                </button>
            {/each}
        {/if}
    </div>
</div>
