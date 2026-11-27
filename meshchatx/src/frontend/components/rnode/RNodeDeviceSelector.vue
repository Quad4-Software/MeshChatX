<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <div class="flex items-center gap-2">
            <div class="p-2 bg-sem-accent/10 rounded-lg text-sem-accent shrink-0">
                <MaterialDesignIcon icon-name="usb-port" class="size-5" />
            </div>
            <h2 class="font-bold text-sem-fg">{{ stepNumber }}. {{ $t("tools.rnode_flasher.select_device") }}</h2>
        </div>

        <div class="space-y-1">
            <label class="rnf-label">{{ $t("tools.rnode_flasher.connection_method") }}</label>
            <div class="grid grid-cols-3 gap-2">
                <button
                    v-for="option in connectionOptions"
                    :key="option.id"
                    type="button"
                    :data-testid="`rnode-transport-${option.id}`"
                    :disabled="!option.available"
                    class="flex flex-col items-center justify-center gap-1 py-2.5 px-2 rounded-xl border text-xs sm:text-sm font-bold transition-all"
                    :class="
                        connectionMethod === option.id
                            ? 'bg-sem-action-primary text-sem-action-primary-text border-transparent'
                            : option.available
                              ? 'bg-sem-surface-muted border-sem-border text-sem-fg-muted hover:bg-sem-surface-muted'
                              : 'bg-sem-surface-muted border-sem-border text-sem-fg-muted opacity-60 cursor-not-allowed'
                    "
                    @click="option.available && emit('update:connectionMethod', option.id)"
                >
                    <MaterialDesignIcon :icon-name="option.icon" class="size-4 sm:size-5" />
                    <span>{{ $t(option.labelKey) }}</span>
                </button>
            </div>
        </div>

        <div v-if="connectionMethod === 'wifi'" class="space-y-1">
            <label class="rnf-label">{{ $t("tools.rnode_flasher.ip_address") }}</label>
            <input
                :value="wifiHost"
                type="text"
                inputmode="decimal"
                autocomplete="off"
                spellcheck="false"
                class="rnf-input"
                :placeholder="$t('tools.rnode_flasher.ip_address_placeholder')"
                @input="emit('update:wifiHost', $event.target.value)"
            />
            <p class="text-[10px] text-sem-fg-muted">
                {{ $t("tools.rnode_flasher.wifi_help") }}
            </p>
        </div>

        <div class="space-y-1">
            <label class="rnf-label">{{ $t("tools.rnode_flasher.product") }}</label>
            <select :value="selectedProduct?.id ?? ''" class="rnf-input" @change="onProductChange">
                <option value="" disabled>{{ $t("tools.rnode_flasher.select_product") }}</option>
                <option v-for="product in products" :key="product.id" :value="product.id">
                    {{ product.name }}
                </option>
            </select>
        </div>

        <div class="space-y-1">
            <label class="rnf-label">{{ $t("tools.rnode_flasher.model") }}</label>
            <select
                :value="selectedModel?.id ?? ''"
                :disabled="!selectedProduct"
                class="rnf-input disabled:opacity-50"
                @change="onModelChange"
            >
                <option value="" disabled>{{ $t("tools.rnode_flasher.select_model") }}</option>
                <template v-if="selectedProduct">
                    <option v-for="model in selectedProduct.models" :key="model.id" :value="model.id">
                        {{ model.name }}
                    </option>
                </template>
            </select>
        </div>

        <button
            v-if="selectedProduct?.platform === 0x70 && connectionMethod === 'serial'"
            :disabled="isEnteringDfuMode"
            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-sem-warning/15 hover:bg-sem-warning/25 px-4 py-2.5 text-sm font-bold text-sem-warning transition-colors disabled:opacity-50"
            @click="emit('enter-dfu')"
        >
            <MaterialDesignIcon
                v-if="isEnteringDfuMode"
                icon-name="loading"
                class="size-4 animate-spin text-sem-warning"
            />
            <MaterialDesignIcon v-else icon-name="restart-alert" class="size-4" />
            <span>
                {{
                    isEnteringDfuMode
                        ? $t("tools.rnode_flasher.entering_dfu_mode")
                        : $t("tools.rnode_flasher.enter_dfu_mode")
                }}
            </span>
        </button>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const props = withDefaults(
    defineProps<{
        stepNumber?: number;
        connectionMethod: string;
        wifiHost?: string;
        selectedProduct?: Record<string, any> | null;
        selectedModel?: Record<string, any> | null;
        products: any[];
        capabilities: Record<string, any>;
        isEnteringDfuMode?: boolean;
    }>(),
    {
        stepNumber: 1,
        wifiHost: "",
        selectedProduct: null,
        selectedModel: null,
        isEnteringDfuMode: false,
    }
);

const emit = defineEmits<{
    "update:connectionMethod": [value: string];
    "update:wifiHost": [value: string];
    "update:selectedProduct": [product: any];
    "update:selectedModel": [model: any];
    "enter-dfu": [];
}>();

const connectionOptions = computed(() => {
    const t = props.capabilities?.transports || {};
    return [
        {
            id: "serial",
            labelKey: "tools.rnode_flasher.serial",
            icon: "usb-port",
            available: Boolean(t.serial?.available),
        },
        {
            id: "bluetooth",
            labelKey: "tools.rnode_flasher.bluetooth",
            icon: "bluetooth",
            available: Boolean(t.bluetooth?.available),
        },
        {
            id: "wifi",
            labelKey: "tools.rnode_flasher.wifi",
            icon: "wifi",
            available: Boolean(t.wifi?.available),
        },
    ];
});

function onProductChange(event: Event) {
    const id = (event.target as HTMLSelectElement).value;
    const product = props.products.find((p) => String(p.id) === String(id)) || null;
    emit("update:selectedProduct", product);
    emit("update:selectedModel", null);
}

function onModelChange(event: Event) {
    const id = (event.target as HTMLSelectElement).value;
    const model = props.selectedProduct?.models?.find((m: any) => String(m.id) === String(id)) || null;
    emit("update:selectedModel", model);
}
</script>

<style scoped>
@reference "../../style.css";
.rnf-label {
    @apply text-xs font-semibold text-sem-fg-muted uppercase tracking-wider;
}
.rnf-input {
    @apply w-full bg-sem-surface-muted border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-sem-focus focus:border-sem-focus-border px-4 py-2.5 transition-all;
}
select.rnf-input {
    appearance: none;
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
    background-position: right 0.5rem center;
    background-repeat: no-repeat;
    background-size: 1.5em 1.5em;
    padding-right: 2.5rem;
}
</style>
