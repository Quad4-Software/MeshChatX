<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { MAX_VISIBLE_REACTION_CHIPS } from "../lib/constants.js";
    import type { ConversationViewerActions, MessageChatItem, MessageReaction } from "../lib/viewerActions.js";

    let {
        reactions = [],
        isOutbound = false,
        chatItem,
        actions,
        showReactButton = true,
        elevated = false,
    }: {
        reactions?: MessageReaction[];
        isOutbound?: boolean;
        chatItem: MessageChatItem;
        actions: ConversationViewerActions;
        showReactButton?: boolean;
        elevated?: boolean;
    } = $props();

    const validReactions = $derived(reactions.filter((reaction) => reaction && typeof reaction === "object"));
    const hiddenReactionCount = $derived(Math.max(0, validReactions.length - MAX_VISIBLE_REACTION_CHIPS));
    const reactionChips = $derived([
        ...validReactions.slice(0, MAX_VISIBLE_REACTION_CHIPS).map((reaction, index) => ({
            kind: "reaction" as const,
            key: reaction.reactionHash || `reaction-${index}-${reaction.emoji || ""}-${reaction.sender || ""}`,
            reaction,
        })),
        ...(hiddenReactionCount > 0 ? [{ kind: "more" as const, key: "reaction-more", reaction: undefined }] : []),
    ]);

    function reactionTitle(reaction?: MessageReaction) {
        if (!reaction) {
            return "";
        }
        try {
            return actions.reactionReactorLabel(reaction.sender) || "";
        } catch (error) {
            console.error(error);
            return "";
        }
    }
</script>

{#if reactions.length > 0 || showReactButton}
    <div
        class="pointer-events-auto absolute z-20 flex w-fit max-w-[calc(100%-0.75rem)] flex-nowrap items-center gap-0.5 {isOutbound
            ? 'right-2 justify-end'
            : 'left-2 justify-start'} {elevated ? 'bottom-9 translate-y-0' : 'bottom-0 translate-y-1/2'}"
    >
        {#each reactionChips as chip, chipIndex (chip.key)}
            <span
                class="inline-flex min-h-4.5 min-w-4.5 shrink-0 cursor-default select-none items-center justify-center rounded-full border border-gray-200/90 bg-white px-1 py-0 text-sm leading-none shadow-sm ring-1 ring-white/90 dark:border-zinc-600/90 dark:bg-zinc-900 dark:ring-zinc-800/90 {chip.kind ===
                'more'
                    ? 'text-[10px] font-semibold text-sem-fg-muted'
                    : ''}"
                style:order={isOutbound ? chipIndex + 2 : chipIndex + 1}
                title={chip.kind === "reaction" ? reactionTitle(chip.reaction) : ""}
            >
                {chip.kind === "more" ? `+${hiddenReactionCount}` : chip.reaction?.emoji || ""}
            </span>
        {/each}
        {#if showReactButton}
            <button
                type="button"
                class="inline-flex shrink-0 items-center justify-center rounded-full border border-dashed border-gray-300 bg-white/95 text-xs leading-none text-gray-400 opacity-0 shadow-sm ring-1 ring-white/90 hover:border-gray-400 hover:text-gray-600 hover:bg-gray-50 group-hover:opacity-100 dark:border-zinc-600 dark:bg-zinc-900/95 text-sem-fg-muted dark:ring-zinc-800/90 dark:hover:border-zinc-500 dark:hover:text-zinc-300 dark:hover:bg-zinc-800 transition-colors {reactions.length >
                0
                    ? 'min-h-4.5 min-w-4.5 px-1 py-0'
                    : 'h-4 w-4 min-h-0 p-0'}"
                style:order={isOutbound ? 1 : reactionChips.length + 1}
                title={t("messages.react")}
                onclick={(event) => {
                    event.stopPropagation();
                    actions.openReactionPicker(chatItem);
                }}
            >
                <MaterialDesignIcon iconName="emoticon-plus-outline" class="size-3" />
            </button>
        {/if}
    </div>
{/if}
