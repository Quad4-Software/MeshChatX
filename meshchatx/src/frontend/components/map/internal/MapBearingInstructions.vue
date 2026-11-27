<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-[calc(0.5rem+2.75rem+0.5rem+2.75rem)] left-1/2 -translate-x-1/2 z-19 w-[min(100vw-2rem,24rem)] pointer-events-auto"
    >
        <div
            class="bg-sem-surface dark:bg-sem-surface backdrop-blur-sm border border-sem-border rounded-xl shadow-lg px-3 py-2 text-xs text-sem-fg"
        >
            <p class="font-medium text-center" :class="showFromHere ? 'mb-2' : ''">
                {{
                    fromGpsActive
                        ? $t("map.bearing_hint_destination")
                        : awaitingSecondTap
                          ? $t("map.bearing_hint_second")
                          : $t("map.bearing_hint_first")
                }}
            </p>
            <button
                v-if="showFromHere"
                type="button"
                class="w-full py-1.5 rounded-lg bg-sem-success hover:bg-sem-success text-white text-[11px] font-semibold transition-colors"
                @click="emit('use-my-location')"
            >
                {{ $t("map.bearing_from_here") }}
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
    defineProps<{
        fromGpsActive?: boolean;
        awaitingSecondTap?: boolean;
    }>(),
    {
        fromGpsActive: false,
        awaitingSecondTap: false,
    }
);

const emit = defineEmits<{
    "use-my-location": [];
}>();

const showFromHere = computed(() => !props.fromGpsActive);
</script>
