<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        role="img"
        :aria-label="iconName"
        fill="currentColor"
        width="100%"
        height="100%"
        style="display: block"
        class="antialiased"
    >
        <path :d="iconPath" fill="currentColor" />
    </svg>
</template>

<script>
import { getMdiIconPath, resolveMdiIconKey } from "../js/mdiIconNames.js";

export default {
    name: "MaterialDesignIcon",
    props: {
        iconName: {
            type: String,
            required: false,
            default: "",
        },
    },
    computed: {
        mdiIconName() {
            return resolveMdiIconKey(this.iconName);
        },
        iconPath() {
            return getMdiIconPath(this.iconName);
        },
    },
};
</script>
