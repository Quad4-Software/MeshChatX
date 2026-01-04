<template>
    <div
        v-if="customImage"
        class="rounded-full overflow-hidden shrink-0 flex items-center justify-center"
        :class="iconClass || 'size-6'"
    >
        <img :src="customImage" class="w-full h-full object-cover" />
    </div>
    <div
        v-else-if="iconName"
        class="p-[10%] rounded-full shrink-0 flex items-center justify-center"
        :style="{ 'background-color': finalBackgroundColor }"
        :class="iconClass || 'size-6'"
    >
        <MaterialDesignIcon :icon-name="iconName" class="size-full" :style="{ color: finalForegroundColor }" />
    </div>
    <div
        v-else
        class="bg-gray-100 dark:bg-zinc-800 text-gray-400 dark:text-zinc-500 p-[15%] rounded-full shrink-0 flex items-center justify-center border border-gray-200 dark:border-zinc-700"
        :class="iconClass || 'size-6'"
    >
        <MaterialDesignIcon icon-name="account" class="w-full h-full" />
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
export default {
    name: "LxmfUserIcon",
    components: {
        MaterialDesignIcon,
    },
    props: {
        customImage: {
            type: String,
            default: "",
        },
        iconName: {
            type: String,
            default: "",
        },
        iconForegroundColour: {
            type: String,
            default: "#6b7280",
        },
        iconBackgroundColour: {
            type: String,
            default: "#e5e7eb",
        },
        iconClass: {
            type: String,
            default: "",
        },
    },
    computed: {
        finalForegroundColor() {
            return this.iconForegroundColour && this.iconForegroundColour !== ""
                ? this.iconForegroundColour
                : "#6b7280";
        },
        finalBackgroundColor() {
            return this.iconBackgroundColour && this.iconBackgroundColour !== ""
                ? this.iconBackgroundColour
                : "#e5e7eb";
        },
    },
};
</script>
