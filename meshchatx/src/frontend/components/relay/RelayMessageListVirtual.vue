<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative w-full shrink-0" :style="{ height: totalSize + 'px' }">
        <div
            v-for="v in virtualItems"
            :key="v.key"
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
import {
    estimateRelayEntryHeight,
    findRelayEntryIndexForMessageKey,
    relayVirtualEntryKey,
} from "./relayMessageListVirtual.js";

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

// Index-keyed measurements (the default) attach row heights to positions, so
// a prepend shifts every cached size onto the wrong entry and the scroll
// anchor computed from scrollHeight deltas lands far off. Stable content keys
// keep each measurement and DOM node on its entry.
const virtualizer = useVirtualizer(
    computed(() => ({
        count: props.entries.length,
        getScrollElement: () => props.getScrollElement() ?? null,
        getItemKey: (index) => relayVirtualEntryKey(props.entries[index], props.page.messageKey) || index,
        estimateSize: (index) => estimateRelayEntryHeight(props.entries[index]),
        overscan: 12,
    }))
);

const virtualItems = computed(() => virtualizer.value.getVirtualItems());
const totalSize = computed(() => virtualizer.value.getTotalSize());

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
