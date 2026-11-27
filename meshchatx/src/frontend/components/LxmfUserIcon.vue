<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-if="customImage"
        class="rounded-full overflow-hidden shrink-0 flex items-center justify-center"
        :class="resolvedShellClass"
        :style="iconStyle"
    >
        <img :src="customImage" class="w-full h-full object-cover" />
    </div>
    <div
        v-else-if="iconName"
        class="rounded-full shrink-0 flex items-center justify-center"
        :style="[iconStyle, { 'background-color': finalBackgroundColor }]"
        :class="resolvedShellClass"
    >
        <MaterialDesignIcon :icon-name="iconName" class="w-[70%] h-[70%]" :style="{ color: finalForegroundColor }" />
    </div>
    <div
        v-else
        class="bg-sem-surface-muted text-sem-fg-muted rounded-full shrink-0 flex items-center justify-center border border-sem-border"
        :class="resolvedShellClass"
        :style="[iconStyle, { 'background-color': fallbackBackgroundColor }]"
    >
        <MaterialDesignIcon icon-name="account" class="w-[70%] h-[70%]" />
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

const props = withDefaults(
    defineProps<{
        customImage?: string;
        iconName?: string;
        iconForegroundColour?: string;
        iconBackgroundColour?: string;
        iconClass?: string;
        iconStyle?: Record<string, any>;
    }>(),
    {
        customImage: "",
        iconName: "",
        iconForegroundColour: "",
        iconBackgroundColour: "",
        iconClass: "",
        iconStyle: () => ({}),
    }
);

const resolvedShellClass = computed(() => {
    const extra = (props.iconClass || "").trim();
    if (
        /\bsize-[\w.]+\b/.test(extra) ||
        /\bw-[\w.]+\b/.test(extra) ||
        /\bh-[\w.]+\b/.test(extra) ||
        /\bmin-w-/.test(extra) ||
        /\bmin-h-/.test(extra)
    ) {
        return extra;
    }
    return ["size-6", extra].filter(Boolean).join(" ").trim();
});

const finalForegroundColor = computed(() =>
    props.iconForegroundColour && props.iconForegroundColour !== "" ? props.iconForegroundColour : "#6b7280"
);

const finalBackgroundColor = computed(() => {
    if (props.iconBackgroundColour && props.iconBackgroundColour !== "") {
        return props.iconBackgroundColour;
    }
    return "#e5e7eb";
});

const fallbackBackgroundColor = computed(() => {
    if (props.iconBackgroundColour && props.iconBackgroundColour !== "") {
        return props.iconBackgroundColour;
    }
    return "";
});
</script>
