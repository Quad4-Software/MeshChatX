<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section class="settings-section break-inside-avoid" :class="sectionClass">
        <header v-if="hasHeader" class="settings-section__header">
            <div>
                <div v-if="eyebrow" class="settings-section__eyebrow">{{ eyebrow }}</div>
                <h2 v-if="title">{{ title }}</h2>
                <p v-if="description">{{ description }}</p>
            </div>
        </header>
        <div class="settings-section__body" :class="bodyClass">
            <slot />
        </div>
    </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

type ClassValue = string | string[] | Record<string, boolean>;

const props = withDefaults(
    defineProps<{
        eyebrow?: string;
        title?: string;
        description?: string;
        sectionClass?: ClassValue;
        bodyClass?: ClassValue;
    }>(),
    {
        eyebrow: "",
        title: "",
        description: "",
        sectionClass: "",
        bodyClass: "",
    }
);

const hasHeader = computed(() => Boolean(props.eyebrow || props.title || props.description));
</script>
