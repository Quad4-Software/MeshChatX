<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        role="img"
        :aria-label="iconName"
        fill="currentColor"
        width="20"
        height="20"
        style="display: block"
        class="antialiased shrink-0"
    >
        <path :d="iconPath" fill="currentColor" />
    </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { getMdiIconPath, resolveMdiIconKey } from "../js/mdiIconNames.js";

const props = withDefaults(
    defineProps<{
        iconName?: string;
    }>(),
    {
        iconName: "",
    }
);

const mdiIconName = computed(() => resolveMdiIconKey(props.iconName));
const iconPath = computed(() => getMdiIconPath(props.iconName));

defineExpose({ mdiIconName });
</script>
