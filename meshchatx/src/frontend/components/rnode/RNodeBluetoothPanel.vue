<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="border border-sem-border bg-sem-surface rounded-2xl shadow-xl overflow-hidden">
        <div class="px-4 sm:px-6 py-4 border-b border-sem-border flex items-center gap-2">
            <MaterialDesignIcon icon-name="bluetooth" class="size-5 text-blue-500" />
            <h3 class="font-bold text-sem-fg">
                {{ $t("tools.rnode_flasher.configure_bluetooth") }}
            </h3>
        </div>
        <div class="p-4 sm:p-6 space-y-4">
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <button class="rnf-action-btn" @click="$emit('action', 'enable-bluetooth')">
                    <MaterialDesignIcon icon-name="bluetooth-connect" class="size-4" />
                    {{ $t("tools.rnode_flasher.enable") }}
                </button>
                <button class="rnf-action-btn" @click="$emit('action', 'disable-bluetooth')">
                    <MaterialDesignIcon icon-name="bluetooth-off" class="size-4" />
                    {{ $t("tools.rnode_flasher.disable") }}
                </button>
                <button
                    class="rnf-action-btn col-span-2 sm:col-span-1 bg-blue-500 text-white! border-none! hover:bg-blue-600"
                    @click="$emit('action', 'pair-bluetooth')"
                >
                    <MaterialDesignIcon icon-name="key-link" class="size-4" />
                    {{ $t("tools.rnode_flasher.start_pairing") }}
                </button>
            </div>
            <p class="text-[10px] text-sem-fg-muted leading-relaxed uppercase tracking-wider">
                {{ $t("tools.rnode_flasher.bluetooth_restart_warning") }}
            </p>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeBluetoothPanel",
    components: { MaterialDesignIcon },
    emits: ["action"],
};
</script>

<style scoped>
@reference "../../style.css";
.rnf-action-btn {
    @apply inline-flex items-center justify-center gap-1.5 rounded-xl bg-sem-surface-muted hover:bg-gray-200 hover:bg-sem-surface-muted px-3 py-2.5 text-[11px] font-bold text-sem-fg-muted border border-sem-border transition-all active:scale-95;
}
</style>
