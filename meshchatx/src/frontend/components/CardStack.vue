<template>
    <div class="card-stack-wrapper" :class="{ 'is-expanded': isExpanded }">
        <div
            v-if="items && items.length > 0"
            class="relative"
            :class="{ 'stack-mode': !isExpanded && items.length > 1, 'grid-mode': isExpanded || items.length === 1 }"
        >
            <!-- Grid Mode (Expanded or only 1 item) -->
            <div v-if="isExpanded || items.length === 1" :class="gridClass">
                <div v-for="(item, index) in items" :key="index" class="w-full">
                    <slot :item="item" :index="index"></slot>
                </div>
            </div>

            <!-- Stack Mode (Collapsed and > 1 item) -->
            <div v-else class="relative" :style="{ height: stackHeight + 'px' }">
                <div
                    v-for="(item, index) in stackedItems"
                    :key="index"
                    class="absolute inset-x-0 top-0 transition-all duration-300 ease-in-out cursor-pointer"
                    :style="getStackStyle(index)"
                    @click="onCardClick(index)"
                >
                    <slot :item="item" :index="index"></slot>

                    <!-- Overlay for non-top cards -->
                    <div
                        v-if="index > 0"
                        class="absolute inset-0 bg-white/20 dark:bg-black/20 rounded-[inherit] pointer-events-none"
                    ></div>
                </div>

                <!-- Controls -->
                <div v-if="items.length > 1" class="absolute -bottom-2 right-0 flex items-center gap-2 z-[60]">
                    <div class="text-xs font-mono text-gray-500 dark:text-gray-400 mr-2">
                        {{ activeIndex + 1 }} / {{ items.length }}
                    </div>
                    <button
                        class="p-1.5 rounded-full bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-700 dark:text-gray-300 transition shadow-sm border border-gray-200 dark:border-zinc-700"
                        title="Previous"
                        @click.stop="prev"
                    >
                        <MaterialDesignIcon icon-name="chevron-left" class="size-5" />
                    </button>
                    <button
                        class="p-1.5 rounded-full bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-700 dark:text-gray-300 transition shadow-sm border border-gray-200 dark:border-zinc-700"
                        title="Next"
                        @click.stop="next"
                    >
                        <MaterialDesignIcon icon-name="chevron-right" class="size-5" />
                    </button>
                </div>
            </div>
        </div>

        <div v-if="items && items.length > 1" class="mt-4 flex justify-center">
            <button
                class="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-xs font-bold text-gray-700 dark:text-gray-300 transition shadow-sm border border-gray-200 dark:border-zinc-700 uppercase tracking-wider"
                @click="isExpanded = !isExpanded"
            >
                <MaterialDesignIcon :icon-name="isExpanded ? 'collapse-all' : 'expand-all'" class="size-4" />
                {{ isExpanded ? "Collapse Stack" : `Show All ${items.length}` }}
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "CardStack",
    components: {
        MaterialDesignIcon,
    },
    props: {
        items: {
            type: Array,
            required: true,
        },
        maxVisible: {
            type: Number,
            default: 3,
        },
        stackHeight: {
            type: Number,
            default: 320,
        },
        gridClass: {
            type: String,
            default: "grid grid-cols-1 gap-4",
        },
    },
    data() {
        return {
            isExpanded: false,
            activeIndex: 0,
        };
    },
    computed: {
        stackedItems() {
            // Reorder items so the active item is at index 0
            const result = [];
            const count = Math.min(this.items.length, this.maxVisible);

            for (let i = 0; i < count; i++) {
                const idx = (this.activeIndex + i) % this.items.length;
                result.push(this.items[idx]);
            }

            return result;
        },
    },
    methods: {
        next() {
            this.activeIndex = (this.activeIndex + 1) % this.items.length;
        },
        prev() {
            this.activeIndex = (this.activeIndex - 1 + this.items.length) % this.items.length;
        },
        onCardClick(index) {
            if (index > 0) {
                // If clicked a background card, bring it to front
                this.activeIndex = (this.activeIndex + index) % this.items.length;
            }
        },
        getStackStyle(index) {
            if (this.isExpanded) return {};

            const offset = 8; // px
            const scaleReduce = 0.05;

            return {
                zIndex: 50 - index,
                transform: `translateY(${index * offset}px) scale(${1 - index * scaleReduce})`,
                opacity: 1 - index * 0.2,
                pointerEvents: index === 0 ? "auto" : "auto",
            };
        },
    },
};
</script>

<style scoped>
.card-stack-wrapper {
    width: 100%;
}

.stack-mode {
    perspective: 1000px;
}
</style>
