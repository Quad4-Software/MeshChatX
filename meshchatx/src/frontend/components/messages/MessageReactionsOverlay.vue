<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="(reactions?.length ?? 0) > 0 || showReactButton"
        class="pointer-events-auto absolute z-20 flex w-fit max-w-[calc(100%-0.75rem)] flex-nowrap items-center gap-0.5"
        :class="[
            isOutbound ? 'right-2 justify-end' : 'left-2 justify-start',
            elevated ? 'bottom-9 translate-y-0' : 'bottom-0 translate-y-1/2',
        ]"
    >
        <span
            v-for="(chip, chipIdx) in reactionChips"
            :key="chip.key"
            class="inline-flex min-h-4.5 min-w-4.5 shrink-0 cursor-default select-none items-center justify-center rounded-full border border-sem-border/90 bg-white px-1 py-0 text-sm leading-none shadow-sm ring-1 ring-white/90 dark:border-zinc-600/90 dark:bg-zinc-900 dark:ring-zinc-800/90"
            :class="chip.kind === 'more' ? 'text-[10px] font-semibold text-sem-fg-muted' : ''"
            :style="{
                order: isOutbound ? chipIdx + 2 : chipIdx + 1,
            }"
            :title="chip.kind === 'reaction' ? reactionTitle(chip.reaction) : ''"
            >{{ chip.kind === "more" ? `+${hiddenReactionCount}` : chip.reaction?.emoji || "" }}</span
        >
        <button
            v-if="showReactButton"
            type="button"
            class="inline-flex shrink-0 items-center justify-center rounded-full border border-dashed border-sem-border bg-white/95 text-xs leading-none text-sem-fg-muted opacity-0 shadow-sm ring-1 ring-white/90 hover:border-gray-400 hover:text-sem-fg-muted hover:bg-sem-surface-muted group-hover:opacity-100 dark:border-zinc-600 dark:bg-zinc-900/95 text-sem-fg-muted dark:ring-zinc-800/90 dark:hover:border-zinc-500 dark:hover:text-zinc-300 dark:hover:bg-sem-surface-raised transition-colors"
            :class="(reactions?.length ?? 0) > 0 ? 'min-h-4.5 min-w-4.5 px-1 py-0' : 'h-4 w-4 min-h-0 p-0'"
            :style="{
                order: isOutbound ? 1 : reactionChips.length + 1,
            }"
            :title="$t('messages.react')"
            @click.stop="cv.openReactionPicker(chatItem)"
        >
            <MaterialDesignIcon icon-name="emoticon-plus-outline" class="size-3" />
        </button>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const MAX_VISIBLE_REACTIONS = 4;

export default {
    name: "MessageReactionsOverlay",
    components: {
        MaterialDesignIcon,
    },
    props: {
        reactions: {
            type: Array,
            default: () => [],
        },
        isOutbound: {
            type: Boolean,
            default: false,
        },
        chatItem: {
            type: Object,
            required: true,
        },
        cv: {
            type: Object,
            required: true,
        },
        showReactButton: {
            type: Boolean,
            default: true,
        },
        elevated: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        visibleReactions() {
            const list = Array.isArray(this.reactions) ? this.reactions : [];
            return list.filter((r) => r && typeof r === "object").slice(0, MAX_VISIBLE_REACTIONS);
        },
        hiddenReactionCount() {
            const list = Array.isArray(this.reactions) ? this.reactions : [];
            const valid = list.filter((r) => r && typeof r === "object");
            return Math.max(0, valid.length - MAX_VISIBLE_REACTIONS);
        },
        reactionChips() {
            const chips = this.visibleReactions.map((r, idx) => ({
                kind: "reaction",
                key: r.reactionHash || `reaction-${idx}-${r.emoji || ""}-${r.sender || ""}`,
                reaction: r,
            }));
            if (this.hiddenReactionCount > 0) {
                chips.push({ kind: "more", key: "reaction-more" });
            }
            return chips;
        },
    },
    methods: {
        reactionTitle(reaction) {
            try {
                if (!reaction || typeof this.cv?.reactionReactorLabel !== "function") {
                    return "";
                }
                return this.cv.reactionReactorLabel(reaction.sender) || "";
            } catch (e) {
                console.error(e);
                return "";
            }
        },
    },
};
</script>
