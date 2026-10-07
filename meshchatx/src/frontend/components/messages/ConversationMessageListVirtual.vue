<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="relative w-full shrink-0" :style="{ height: totalSize + 'px' }">
        <div
            v-for="v in virtualItems"
            :key="groups[v.index]?.key ?? v.index"
            :ref="measureElement"
            :data-index="v.index"
            class="absolute left-0 top-0 w-full box-border px-0 [overflow-anchor:none]"
            :class="{ 'msg-enter': freshInboundKeys.has(groups[v.index]?.key) }"
            :style="{ transform: `translateY(${v.start}px)` }"
        >
            <ConversationMessageEntry :entry="groups[v.index]" :cv="cv" />
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import ConversationMessageEntry from "./ConversationMessageEntry.vue";
import {
    diffFreshInboundKeys,
    estimateGroupHeight,
    findDisplayGroupIndexForMessageHash,
} from "./messageListVirtual.js";

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
    // Identifies the conversation (peer hash). Switching peers resets the
    // seen-key tracking so existing history never animates on open.
    listKey: {
        type: String,
        default: "",
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

// Keys of inbound groups appended while the list is live. They get a short
// entrance animation on the inner entry; scroll remounts and history
// prepends stay static because only tail additions are tracked.
const freshInboundKeys = ref(new Set());
let knownKeys = new Set();
let primedKey = null;

watch([() => props.groups, () => props.listKey], ([groups]) => {
    if (primedKey !== props.listKey) {
        primedKey = props.listKey;
        knownKeys = new Set(groups.map((g) => g.key));
        freshInboundKeys.value = new Set();
        return;
    }
    const { fresh, nextKeys } = diffFreshInboundKeys(groups, knownKeys);
    knownKeys = nextKeys;
    if (!fresh.length) {
        return;
    }
    const merged = new Set(freshInboundKeys.value);
    fresh.forEach((k) => merged.add(k));
    freshInboundKeys.value = merged;
    setTimeout(() => {
        const pruned = new Set(freshInboundKeys.value);
        fresh.forEach((k) => pruned.delete(k));
        freshInboundKeys.value = pruned;
    }, 700);
});

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
