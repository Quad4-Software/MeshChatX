<template>
    <div
        v-if="iconName"
        class="p-2 rounded-full"
        :style="{ color: iconForegroundColour, 'background-color': iconBackgroundColour }"
    >
        <MaterialDesignIcon :icon-name="iconName" :class="iconClass" />
    </div>
    <div v-else class="bg-gray-200 dark:bg-zinc-700 text-gray-500 dark:text-gray-400 p-2 rounded-full">
        <MaterialDesignIcon icon-name="account-outline" :class="iconClass" />
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
        iconName: {
            type: String,
            default: "",
        },
        iconForegroundColour: {
            type: String,
            default: "",
        },
        iconBackgroundColour: {
            type: String,
            default: "",
        },
        iconClass: {
            type: String,
            default: "size-6",
        },
    },
};
</script>
