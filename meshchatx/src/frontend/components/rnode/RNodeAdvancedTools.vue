<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <div class="text-xs font-bold text-gray-400 dark:text-zinc-600 uppercase tracking-widest">
            {{ $t("tools.rnode_flasher.advanced_tools") }}
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            <button
                v-for="action in availableActions"
                :key="action.id"
                type="button"
                class="rnf-action-btn"
                :class="{ 'rnf-action-btn--danger': action.danger }"
                @click="$emit('action', action.id)"
            >
                <MaterialDesignIcon :icon-name="action.icon" class="size-4" />
                <span>{{ $t(action.labelKey) }}</span>
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const ALL_ACTIONS = [
    { id: "detect", icon: "magnify", labelKey: "tools.rnode_flasher.detect_rnode" },
    { id: "diagnose", icon: "stethoscope", labelKey: "tools.rnode_flasher.run_diagnostics" },
    { id: "reboot", icon: "restart", labelKey: "tools.rnode_flasher.reboot_rnode" },
    { id: "read-display", icon: "monitor", labelKey: "tools.rnode_flasher.read_display" },
    { id: "dump-eeprom", icon: "database-export", labelKey: "tools.rnode_flasher.dump_eeprom" },
    {
        id: "wipe-eeprom",
        icon: "eraser",
        labelKey: "tools.rnode_flasher.wipe_eeprom",
        danger: true,
    },
];

export default {
    name: "RNodeAdvancedTools",
    components: { MaterialDesignIcon },
    props: {
        disabledActions: {
            type: Array,
            default: () => [],
        },
    },
    emits: ["action"],
    computed: {
        availableActions() {
            return ALL_ACTIONS.filter((a) => !this.disabledActions.includes(a.id));
        },
    },
};
</script>

<style scoped>
.rnf-action-btn {
    @apply inline-flex items-center justify-center gap-1.5 rounded-xl bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 px-3 py-2.5 text-[11px] font-bold text-gray-700 dark:text-zinc-300 border border-gray-200 dark:border-zinc-700 transition-all active:scale-95;
}
.rnf-action-btn--danger {
    @apply bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-100 dark:border-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/40;
}
</style>
