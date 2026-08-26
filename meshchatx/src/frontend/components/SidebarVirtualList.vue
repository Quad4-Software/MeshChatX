<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="scrollRef" class="h-full overflow-y-auto overflow-x-hidden" @scroll="$emit('scroll', $event)">
        <template v-if="virtualize">
            <div class="relative w-full" :style="{ height: totalSize + 'px' }">
                <div
                    v-for="v in virtualItems"
                    :key="itemKey(items[v.index], v.index)"
                    :ref="measureElement"
                    :data-index="v.index"
                    class="absolute left-0 top-0 w-full box-border [overflow-anchor:none]"
                    :style="{ transform: `translateY(${v.start}px)` }"
                >
                    <slot name="item" :item="items[v.index]" :index="v.index" />
                </div>
            </div>
        </template>
        <template v-else>
            <div v-for="(item, index) in items" :key="itemKey(item, index)">
                <slot name="item" :item="item" :index="index" />
            </div>
        </template>
    </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import { estimateSidebarRowHeight } from "../js/sidebarListVirtual.js";

const props = defineProps({
    items: {
        type: Array,
        required: true,
    },
    itemKey: {
        type: Function,
        default: (item, index) => item?.destination_hash ?? item?.id ?? index,
    },
    estimateSize: {
        type: Function,
        default: estimateSidebarRowHeight,
    },
    overscan: {
        type: Number,
        default: 8,
    },
    virtualize: {
        type: Boolean,
        default: true,
    },
});

defineEmits(["scroll"]);

const scrollRef = ref(null);

const virtualizer = useVirtualizer(
    computed(() => ({
        count: props.items.length,
        getScrollElement: () => scrollRef.value,
        estimateSize: (index) => props.estimateSize(props.items[index], index),
        overscan: props.overscan,
    }))
);

const virtualItems = computed(() => virtualizer.value.getVirtualItems());
const totalSize = computed(() => virtualizer.value.getTotalSize());

function measureElement(el) {
    if (el) {
        virtualizer.value.measureElement(el);
    }
}

defineExpose({
    scrollRef,
});
</script>
