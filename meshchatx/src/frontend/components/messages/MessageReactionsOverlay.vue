<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="(reactions?.length ?? 0) > 0 || showReactButton"
        class="pointer-events-auto absolute z-20 flex w-fit max-w-[calc(100%-0.75rem)] flex-wrap items-center gap-0.5"
        :class="[
            isOutbound ? 'right-2 justify-end' : 'left-2 justify-start',
            elevated ? 'bottom-9 translate-y-0' : 'bottom-0 translate-y-1/2',
        ]"
    >
        <span
            v-for="(r, ridx) in reactions"
            :key="r.reactionHash || ridx"
            class="inline-flex min-h-4.5 min-w-4.5 cursor-default select-none items-center justify-center rounded-full border border-gray-200/90 bg-white px-1 py-0 text-sm leading-none shadow-sm ring-1 ring-white/90 dark:border-zinc-600/90 dark:bg-zinc-900 dark:ring-zinc-800/90"
            :style="{
                order: isOutbound ? ridx + 2 : ridx + 1,
            }"
            :title="cv.reactionReactorLabel(r.sender)"
            >{{ r.emoji }}</span
        >
        <button
            v-if="showReactButton"
            type="button"
            class="inline-flex items-center justify-center rounded-full border border-dashed border-gray-300 bg-white/95 text-xs leading-none text-gray-400 opacity-0 shadow-sm ring-1 ring-white/90 hover:border-gray-400 hover:text-gray-600 hover:bg-gray-50 group-hover:opacity-100 dark:border-zinc-600 dark:bg-zinc-900/95 dark:text-zinc-500 dark:ring-zinc-800/90 dark:hover:border-zinc-500 dark:hover:text-zinc-300 dark:hover:bg-zinc-800 transition-colors"
            :class="(reactions?.length ?? 0) > 0 ? 'min-h-4.5 min-w-4.5 px-1 py-0' : 'h-4 w-4 min-h-0 p-0'"
            :style="{
                order: isOutbound ? 1 : (reactions?.length ?? 0) + 1,
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
};
</script>
