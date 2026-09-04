<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="entry.type === 'dateDivider'"
        class="flex items-center justify-center gap-3 w-full my-3 shrink-0 px-2 select-none"
        role="separator"
        :aria-label="page.formatDateDividerLabel(entry.dayKey)"
    >
        <span class="h-px w-10 shrink-0 bg-sem-border sm:w-14" aria-hidden="true" />
        <span
            class="max-w-[min(100%,18rem)] text-center text-[11px] font-medium leading-snug tracking-wide text-sem-fg-muted"
        >
            {{ page.formatDateDividerLabel(entry.dayKey) }}
        </span>
        <span class="h-px w-10 shrink-0 bg-sem-border sm:w-14" aria-hidden="true" />
    </div>
    <div v-else-if="entry.type === 'presenceGroup'" class="px-2 py-1">
        <button
            type="button"
            class="mx-auto flex max-w-full items-center gap-1 rounded-md px-2 py-0.5 text-xs italic text-sem-fg-muted transition-colors hover:bg-sem-surface/50 hover:text-sem-fg"
            :aria-expanded="expanded"
            @click="page.togglePresenceGroup(entry.id)"
        >
            <MaterialDesignIcon
                :icon-name="expanded ? 'chevron-down' : 'chevron-right'"
                class="size-3.5 shrink-0 opacity-70"
            />
            <span class="truncate">{{ page.formatPresenceGroupSummary(entry) }}</span>
        </button>
        <div v-if="expanded" class="mt-1 space-y-0.5">
            <div
                v-for="(msg, idx) in entry.messages"
                :key="page.messageKey(msg) || idx"
                class="py-0.5 text-center text-xs italic text-sem-fg-muted"
                :data-msg-key="page.messageKey(msg)"
            >
                {{ msg.text }}
            </div>
        </div>
    </div>
    <div
        v-else-if="isSystemLike"
        class="py-0.5 text-center text-xs italic"
        :class="entry.msg.kind === 'error' ? 'text-sem-danger' : 'text-sem-fg-muted'"
        :data-msg-key="page.messageKey(entry.msg)"
    >
        {{ entry.msg.text }}
    </div>
    <div
        v-else-if="entry.msg && entry.msg.kind === 'action'"
        class="rounded-lg px-2 py-1 text-sm italic"
        :class="entry.msg.mention ? 'bg-sem-warning/15' : ''"
        :data-msg-key="page.messageKey(entry.msg)"
    >
        <span class="mr-1 text-xs text-sem-fg-muted">{{ page.formatTime(entry.msg.ts) }}</span>
        * {{ page.displayName(entry.msg) }}
        <!-- eslint-disable vue/no-v-html -- sanitized via renderMessageHtml -->
        <span
            class="wrap-break-word"
            @click="page.handleMessageHtmlClick($event)"
            v-html="page.renderMessageHtml(entry.msg.text)"
        ></span>
        <!-- eslint-enable vue/no-v-html -->
    </div>
    <div
        v-else-if="entry.msg"
        class="rounded-lg px-2 py-1 text-sm"
        :class="entry.msg.mention ? 'bg-sem-warning/15' : 'hover:bg-sem-surface/40 dark:hover:bg-sem-surface/20'"
        :data-msg-key="page.messageKey(entry.msg)"
        @contextmenu="page.openMessageContextMenu($event, entry.msg)"
    >
        <span class="mr-1.5 text-xs text-sem-fg-muted">{{ page.formatTime(entry.msg.ts) }}</span>
        <span class="mr-1.5 font-semibold" :style="page.nameStyle(entry.msg)">{{ page.displayName(entry.msg) }}:</span>
        <!-- eslint-disable vue/no-v-html -- sanitized via renderMessageHtml -->
        <span
            class="whitespace-pre-wrap wrap-break-word"
            @click="page.handleMessageHtmlClick($event)"
            v-html="page.renderMessageHtml(entry.msg.text)"
        ></span>
        <!-- eslint-enable vue/no-v-html -->
    </div>
</template>

<script setup>
import { computed } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const props = defineProps({
    entry: {
        type: Object,
        required: true,
    },
    page: {
        type: Object,
        required: true,
    },
});

const isSystemLike = computed(() => {
    const kind = props.entry?.msg?.kind;
    return kind === "system" || kind === "notice" || kind === "error";
});

const expanded = computed(() => {
    if (props.entry?.type !== "presenceGroup") {
        return false;
    }
    return props.page.isPresenceGroupExpanded(props.entry.id);
});
</script>
