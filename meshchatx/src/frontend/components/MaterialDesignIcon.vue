<template>
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        role="img"
        :aria-label="iconName"
        fill="currentColor"
        width="100%"
        height="100%"
        style="display: inline-block; vertical-align: middle; shape-rendering: inherit"
        class="antialiased"
    >
        <path :d="iconPath" />
    </svg>
</template>

<script>
import * as mdi from "@mdi/js";

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
            if (!this.iconName) return "mdiAccountOutline";

            // if already starts with mdi and is camelCase, return as is
            if (this.iconName.startsWith("mdi") && /[A-Z]/.test(this.iconName)) {
                return this.iconName;
            }

            // convert icon name from lxmf icon appearance to format expected by the @mdi/js library
            // e.g: alien-outline -> mdiAlienOutline
            return (
                "mdi" +
                this.iconName
                    .split("-")
                    .filter((word) => word.length > 0)
                    .map((word) => {
                        // capitalise first letter of each part
                        return word.charAt(0).toUpperCase() + word.slice(1);
                    })
                    .join("")
            );
        },
        iconPath() {
            if (!mdi || Object.keys(mdi).length === 0) {
                console.error("MDI library not loaded or empty");
                return "";
            }

            const name = this.mdiIconName;
            const path = mdi[name];

            if (path) return path;

            // fallback logic
            console.warn(`Icon not found: ${name} (original: ${this.iconName})`);
            return mdi["mdiHelpCircleOutline"] || mdi["mdiProgressQuestion"] || "";
        },
    },
};
</script>
