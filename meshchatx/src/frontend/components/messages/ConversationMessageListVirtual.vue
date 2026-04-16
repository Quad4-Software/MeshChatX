<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative w-full shrink-0" :style="{ height: totalSize + 'px' }">
        <div
            v-for="v in virtualItems"
            :key="groups[v.index]?.key ?? v.index"
            :ref="measureElement"
            :data-index="v.index"
            class="absolute left-0 top-0 w-full box-border px-0"
            :style="{ transform: `translateY(${v.start}px)` }"
        >
            <ConversationMessageEntry :entry="groups[v.index]" :cv="cv" />
        </div>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import ConversationMessageEntry from "./ConversationMessageEntry.vue";
import { estimateGroupHeight, findDisplayGroupIndexForMessageHash } from "./messageListVirtual.js";

const props = defineProps({
    groups: {
        type: Array,
        required: true,
    },
    getScrollElement: {
        type: Function,
        required: true,
    },
    cv: {
        type: Object,
        required: true,
    },
});

const virtualizer = useVirtualizer(
    computed(() => ({
        count: props.groups.length,
        getScrollElement: () => props.getScrollElement() ?? null,
        estimateSize: (index) => estimateGroupHeight(props.groups[index]),
        overscan: 10,
    }))
);

const virtualItems = computed(() => virtualizer.value.getVirtualItems());
const totalSize = computed(() => virtualizer.value.getTotalSize());

function measureElement(el) {
    if (el) {
        virtualizer.value.measureElement(el);
    }
}

function scrollToMessageHash(hash) {
    const idx = findDisplayGroupIndexForMessageHash(props.groups, hash);
    if (idx < 0) {
        return;
    }
    virtualizer.value.scrollToIndex(idx, { align: "center", behavior: "smooth" });
}

function scrollToBottom() {
    const n = props.groups.length;
    if (n === 0) {
        return;
    }
    virtualizer.value.scrollToIndex(n - 1, { align: "end", behavior: "auto" });
}

function getTotalSize() {
    return virtualizer.value.getTotalSize();
}

defineExpose({
    scrollToMessageHash,
    scrollToBottom,
    getTotalSize,
});
</script>
