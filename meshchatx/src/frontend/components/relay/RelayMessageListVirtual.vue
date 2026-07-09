<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative w-full shrink-0" :style="{ height: totalSize + 'px' }">
        <div
            v-for="v in virtualItems"
            :key="entryKey(entries[v.index], v.index)"
            :ref="measureElement"
            :data-index="v.index"
            class="absolute left-0 top-0 w-full box-border px-0 [overflow-anchor:none]"
            :style="{ transform: `translateY(${v.start}px)` }"
        >
            <RelayMessageEntry :entry="entries[v.index]" :page="page" />
        </div>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import RelayMessageEntry from "./RelayMessageEntry.vue";
import { estimateRelayEntryHeight, findRelayEntryIndexForMessageKey } from "./relayMessageListVirtual.js";

const props = defineProps({
    entries: {
        type: Array,
        required: true,
    },
    getScrollElement: {
        type: Function,
        required: true,
    },
    page: {
        type: Object,
        required: true,
    },
});

const virtualizer = useVirtualizer(
    computed(() => ({
        count: props.entries.length,
        getScrollElement: () => props.getScrollElement() ?? null,
        estimateSize: (index) => estimateRelayEntryHeight(props.entries[index]),
        overscan: 12,
    }))
);

const virtualItems = computed(() => virtualizer.value.getVirtualItems());
const totalSize = computed(() => virtualizer.value.getTotalSize());

function entryKey(entry, index) {
    if (!entry) {
        return `idx-${index}`;
    }
    if (entry.type === "dateDivider") {
        return `date-${entry.dayKey}-${index}`;
    }
    const msgKey = props.page.messageKey(entry.msg);
    return msgKey ? `${msgKey}-${index}` : `idx-${index}`;
}

function measureElement(el) {
    if (el) {
        virtualizer.value.measureElement(el);
    }
}

function scrollToMessageKey(key) {
    const idx = findRelayEntryIndexForMessageKey(props.entries, key, props.page.messageKey);
    if (idx < 0) {
        return;
    }
    virtualizer.value.scrollToIndex(idx, { align: "center", behavior: "smooth" });
}

function scrollToBottom() {
    const n = props.entries.length;
    if (n === 0) {
        return;
    }
    virtualizer.value.scrollToIndex(n - 1, { align: "end", behavior: "auto" });
}

defineExpose({
    scrollToMessageKey,
    scrollToBottom,
});
</script>
