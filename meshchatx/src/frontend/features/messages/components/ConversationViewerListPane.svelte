<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import ConversationMessageEntry, { type MessageDisplayEntry } from "./ConversationMessageEntry.svelte";
    import ConversationMessageListVirtual from "./ConversationMessageListVirtual.svelte";
    import type { ConversationViewerActions } from "../lib/viewerActions.js";

    let {
        messagesScroll = $bindable(undefined as HTMLDivElement | undefined),
        groups = [] as MessageDisplayEntry[],
        useVirtualMessageList = false,
        hasMorePrevious = false,
        isLoadingPrevious = false,
        autoScrollOnNewMessage = true,
        messagesViewportReady = true,
        actions,
        onloadprevious,
        onscrolltobottom,
        onscroll,
    }: {
        messagesScroll?: HTMLDivElement;
        groups?: MessageDisplayEntry[];
        useVirtualMessageList?: boolean;
        hasMorePrevious?: boolean;
        isLoadingPrevious?: boolean;
        autoScrollOnNewMessage?: boolean;
        messagesViewportReady?: boolean;
        actions: ConversationViewerActions;
        onloadprevious?: () => void;
        onscrolltobottom?: () => void;
        onscroll?: (event: Event) => void;
    } = $props();

    let messageListVirtual: ConversationMessageListVirtual | undefined = $state();

    export function scrollToMessageHash(hash: string) {
        if (useVirtualMessageList) {
            messageListVirtual?.scrollToMessageHash(hash);
        }
    }

    export function scrollToBottom() {
        if (useVirtualMessageList) {
            messageListVirtual?.scrollToBottom();
        }
    }
</script>

<div class="relative flex min-h-0 flex-1 flex-col">
    <div
        id="messages"
        bind:this={messagesScroll}
        class="min-h-0 flex-1 overflow-y-auto bg-sem-canvas"
        data-message-list-mode={useVirtualMessageList ? "virtual" : "flow"}
        aria-busy={!messagesViewportReady}
        onscroll={(e) => onscroll?.(e)}
    >
        <div class="relative flex min-w-0 flex-col px-3 sm:px-4 {useVirtualMessageList ? '' : 'py-5'}">
            {#if hasMorePrevious}
                <button
                    id="load-previous"
                    type="button"
                    class="mx-auto rounded-full border border-sem-border bg-sem-surface px-4 py-2 text-sm text-sem-fg-muted shadow-xs hover:bg-sem-surface-muted {useVirtualMessageList
                        ? 'absolute top-2 left-1/2 z-20 -translate-x-1/2'
                        : 'mb-2'}"
                    disabled={isLoadingPrevious}
                    onclick={() => onloadprevious?.()}
                >
                    {isLoadingPrevious ? t("common.loading") : t("messages.load_previous")}
                </button>
            {/if}
            {#if useVirtualMessageList}
                <ConversationMessageListVirtual
                    bind:this={messageListVirtual}
                    {groups}
                    getScrollElement={() => messagesScroll}
                    {actions}
                />
            {:else}
                <div class="flex min-w-0 flex-col [overflow-anchor:none]">
                    {#each groups as entry (entry.key)}
                        <ConversationMessageEntry {entry} {actions} />
                    {/each}
                </div>
            {/if}
        </div>
    </div>

    {#if !autoScrollOnNewMessage && messagesViewportReady}
        <button
            type="button"
            class="absolute bottom-3 left-1/2 z-20 flex size-11 -translate-x-1/2 items-center justify-center rounded-full border border-sem-border bg-sem-surface shadow-md"
            title={t("messages.scroll_to_bottom")}
            onclick={() => onscrolltobottom?.()}
        >
            <MaterialDesignIcon iconName="chevron-down" class="size-5" />
        </button>
    {/if}
</div>
