<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="image" class="p-4 rounded-2xl bg-zinc-950 flex flex-col items-center gap-2 border border-zinc-800">
        <img :src="image" alt="RNode display" class="h-24 sm:h-28 pixelated" />
        <button
            type="button"
            class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 hover:text-zinc-200"
            @click="$emit('clear')"
        >
            {{ $t("common.clear") }}
        </button>
    </div>
</template>

<script>
export default {
    name: "RNodeDeviceDisplay",
    props: {
        image: { type: String, default: null },
    },
    emits: ["clear"],
};
</script>

<style scoped>
.pixelated {
    image-rendering: pixelated;
}
</style>
