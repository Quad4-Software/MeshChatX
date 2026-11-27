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
            class="inline-flex min-h-4.5 min-w-4.5 shrink-0 cursor-default select-none items-center justify-center rounded-full border border-sem-border/90 bg-sem-surface px-1 py-0 text-sm leading-none shadow-sm ring-1 ring-white/90 border-sem-border/90 dark:bg-sem-surface dark:ring-zinc-800/90"
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
            class="inline-flex shrink-0 items-center justify-center rounded-full border border-dashed border-sem-border bg-sem-surface text-xs leading-none text-sem-fg-muted opacity-0 shadow-sm ring-1 ring-white/90 hover:border-sem-border hover:text-sem-fg-muted hover:bg-sem-surface-muted group-hover:opacity-100 border-sem-border dark:bg-sem-surface text-sem-fg-muted dark:ring-zinc-800/90 dark:hover:border-sem-border dark:hover:text-sem-fg-secondary dark:hover:bg-sem-surface-raised transition-colors"
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

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const MAX_VISIBLE_REACTIONS = 4;

const props = withDefaults(
    defineProps<{
        reactions?: any[];
        isOutbound?: boolean;
        chatItem: Record<string, any>;
        cv: Record<string, any>;
        showReactButton?: boolean;
        elevated?: boolean;
    }>(),
    {
        reactions: () => [],
        isOutbound: false,
        showReactButton: true,
        elevated: false,
    }
);

const validReactions = computed(() => {
    const list = Array.isArray(props.reactions) ? props.reactions : [];
    return list.filter((r) => r && typeof r === "object");
});

const visibleReactions = computed(() => validReactions.value.slice(0, MAX_VISIBLE_REACTIONS));

const hiddenReactionCount = computed(() => Math.max(0, validReactions.value.length - MAX_VISIBLE_REACTIONS));

const reactionChips = computed(() => {
    const chips: { kind: string; key: string; reaction?: any }[] = visibleReactions.value.map((r, idx) => ({
        kind: "reaction",
        key: r.reactionHash || `reaction-${idx}-${r.emoji || ""}-${r.sender || ""}`,
        reaction: r,
    }));
    if (hiddenReactionCount.value > 0) {
        chips.push({ kind: "more", key: "reaction-more" });
    }
    return chips;
});

function reactionTitle(reaction: any) {
    try {
        if (!reaction || typeof props.cv?.reactionReactorLabel !== "function") {
            return "";
        }
        return props.cv.reactionReactorLabel(reaction.sender) || "";
    } catch (e) {
        console.error(e);
        return "";
    }
}
</script>
