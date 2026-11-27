<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="border border-sem-border bg-sem-surface rounded-2xl shadow-xl overflow-hidden">
        <div class="px-4 sm:px-6 py-4 border-b border-sem-border flex items-center gap-2">
            <MaterialDesignIcon icon-name="radio-tower" class="size-5 text-sem-success" />
            <h3 class="font-bold text-sem-fg">
                {{ $t("tools.rnode_flasher.configure_tnc") }}
            </h3>
        </div>
        <div class="p-4 sm:p-6 space-y-4">
            <div class="grid grid-cols-2 gap-3">
                <div class="space-y-1">
                    <label class="rnf-input-label">{{ $t("tools.rnode_flasher.frequency") }}</label>
                    <input :value="frequency" type="number" class="rnf-config-input" @input="onUpdateFrequency" />
                </div>
                <div class="space-y-1">
                    <label class="rnf-input-label">{{ $t("tools.rnode_flasher.tx_power") }}</label>
                    <input :value="txPower" type="number" class="rnf-config-input" @input="onUpdateTxPower" />
                </div>
                <div class="space-y-1">
                    <label class="rnf-input-label">{{ $t("tools.rnode_flasher.bandwidth") }}</label>
                    <select :value="bandwidth" class="rnf-config-input" @change="onUpdateBandwidth">
                        <option v-for="bw in bandwidths" :key="bw" :value="bw">{{ bw / 1000 }} KHz</option>
                    </select>
                </div>
                <div class="space-y-1">
                    <label class="rnf-input-label">{{ $t("tools.rnode_flasher.spreading_factor") }}</label>
                    <select :value="spreadingFactor" class="rnf-config-input" @change="onUpdateSpreadingFactor">
                        <option v-for="sf in spreadingFactors" :key="sf" :value="sf">
                            {{ sf }}
                        </option>
                    </select>
                </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
                <button
                    class="rnf-action-btn bg-sem-action-primary text-sem-action-primary-text! border-none! hover:bg-sem-action-primary-hover"
                    @click="emit('action', 'enable-tnc')"
                >
                    {{ $t("tools.rnode_flasher.enable") }}
                </button>
                <button class="rnf-action-btn" @click="emit('action', 'disable-tnc')">
                    {{ $t("tools.rnode_flasher.disable") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const BANDWIDTHS = [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000];
const SPREADING_FACTORS = [7, 8, 9, 10, 11, 12];

withDefaults(
    defineProps<{
        frequency?: number;
        bandwidth?: number;
        txPower?: number;
        spreadingFactor?: number;
    }>(),
    {
        frequency: 917375000,
        bandwidth: 250000,
        txPower: 22,
        spreadingFactor: 11,
    }
);

const emit = defineEmits<{
    "update:frequency": [value: number];
    "update:bandwidth": [value: number];
    "update:txPower": [value: number];
    "update:spreadingFactor": [value: number];
    action: [action: string];
}>();

const bandwidths = BANDWIDTHS;
const spreadingFactors = SPREADING_FACTORS;

function numValue(event: Event) {
    return Number((event.target as HTMLInputElement).value);
}

function onUpdateFrequency(event: Event) {
    emit("update:frequency", numValue(event));
}

function onUpdateTxPower(event: Event) {
    emit("update:txPower", numValue(event));
}

function onUpdateBandwidth(event: Event) {
    emit("update:bandwidth", numValue(event));
}

function onUpdateSpreadingFactor(event: Event) {
    emit("update:spreadingFactor", numValue(event));
}
</script>

<style scoped>
@reference "../../style.css";
.rnf-input-label {
    @apply text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest;
}
.rnf-config-input {
    @apply w-full bg-sem-surface-muted border border-sem-border text-sem-fg text-[12px] rounded-lg focus:ring-1 focus:ring-sem-focus focus:border-sem-focus-border px-3 py-2 transition-all;
}
.rnf-action-btn {
    @apply inline-flex items-center justify-center gap-1.5 rounded-xl bg-sem-surface-muted hover:bg-sem-surface-raised px-3 py-2.5 text-[11px] font-bold text-sem-fg-muted border border-sem-border transition-all active:scale-95;
}
</style>
