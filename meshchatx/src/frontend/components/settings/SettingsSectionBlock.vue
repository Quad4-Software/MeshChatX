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

<script>
export default {
    name: "SettingsSectionBlock",
    props: {
        eyebrow: {
            type: String,
            default: "",
        },
        title: {
            type: String,
            default: "",
        },
        description: {
            type: String,
            default: "",
        },
        sectionClass: {
            type: [String, Array, Object],
            default: "",
        },
        bodyClass: {
            type: [String, Array, Object],
            default: "",
        },
    },
    computed: {
        hasHeader() {
            return Boolean(this.eyebrow || this.title || this.description);
        },
    },
};
</script>
