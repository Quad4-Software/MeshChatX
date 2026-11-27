<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <div class="text-xs font-bold text-sem-fg-muted uppercase tracking-widest">
            {{ $t("tools.rnode_flasher.advanced_tools") }}
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            <button
                v-for="action in availableActions"
                :key="action.id"
                type="button"
                class="rnf-action-btn"
                :class="{ 'rnf-action-btn--danger': action.danger }"
                @click="emit('action', action.id)"
            >
                <MaterialDesignIcon :icon-name="action.icon" class="size-4" />
                <span>{{ $t(action.labelKey) }}</span>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

interface RNodeAction {
    id: string;
    icon: string;
    labelKey: string;
    danger?: boolean;
}

const ALL_ACTIONS: RNodeAction[] = [
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

const props = withDefaults(
    defineProps<{
        disabledActions?: string[];
    }>(),
    {
        disabledActions: () => [],
    }
);

const emit = defineEmits<{
    action: [action: string];
}>();

const availableActions = computed(() => ALL_ACTIONS.filter((a) => !props.disabledActions.includes(a.id)));
</script>

<style scoped>
@reference "../../style.css";
.rnf-action-btn {
    @apply inline-flex items-center justify-center gap-1.5 rounded-xl bg-sem-surface-muted hover:bg-sem-surface-raised px-3 py-2.5 text-[11px] font-bold text-sem-fg-muted border border-sem-border transition-all active:scale-95;
}
.rnf-action-btn--danger {
    @apply bg-sem-surface text-sem-danger border-sem-danger/30 hover:bg-sem-danger/10;
}
</style>
