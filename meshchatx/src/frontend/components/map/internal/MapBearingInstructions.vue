<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-[calc(0.5rem+2.75rem+0.5rem+2.75rem)] left-1/2 -translate-x-1/2 z-19 w-[min(100vw-2rem,24rem)] pointer-events-auto"
    >
        <div
            class="bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm border border-gray-200 dark:border-zinc-700 rounded-xl shadow-lg px-3 py-2 text-xs text-gray-800 dark:text-zinc-200"
        >
            <p class="font-medium text-center" :class="showFromHere ? 'mb-2' : ''">{{ instructionText }}</p>
            <button
                v-if="showFromHere"
                type="button"
                class="w-full py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition-colors"
                @click="$emit('use-my-location')"
            >
                {{ $t("map.bearing_from_here") }}
            </button>
        </div>
    </div>
</template>

<script>
export default {
    name: "MapBearingInstructions",
    props: {
        fromGpsActive: { type: Boolean, default: false },
        awaitingSecondTap: { type: Boolean, default: false },
    },
    emits: ["use-my-location"],
    computed: {
        instructionText() {
            if (this.fromGpsActive) {
                return this.$t("map.bearing_hint_destination");
            }
            if (this.awaitingSecondTap) {
                return this.$t("map.bearing_hint_second");
            }
            return this.$t("map.bearing_hint_first");
        },
        showFromHere() {
            return !this.fromGpsActive;
        },
    },
};
</script>
