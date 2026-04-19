<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <div class="flex items-center gap-2">
            <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400 shrink-0">
                <MaterialDesignIcon icon-name="usb-port" class="size-5" />
            </div>
            <h2 class="font-bold text-gray-900 dark:text-zinc-100">
                {{ stepNumber }}. {{ $t("tools.rnode_flasher.select_device") }}
            </h2>
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
                            ? 'bg-blue-600 text-white border-blue-600'
                            : option.available
                              ? 'bg-gray-50 dark:bg-zinc-800/50 border-gray-200 dark:border-zinc-800 text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800'
                              : 'bg-gray-100 dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 text-gray-400 dark:text-zinc-600 cursor-not-allowed'
                    "
                    @click="option.available && $emit('update:connectionMethod', option.id)"
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
                @input="$emit('update:wifiHost', $event.target.value)"
            />
            <p class="text-[10px] text-gray-500 dark:text-zinc-500">
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
            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/40 px-4 py-2.5 text-sm font-bold text-amber-700 dark:text-amber-400 transition-colors disabled:opacity-50"
            @click="$emit('enter-dfu')"
        >
            <v-progress-circular v-if="isEnteringDfuMode" indeterminate size="16" width="2" />
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

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeDeviceSelector",
    components: { MaterialDesignIcon },
    props: {
        stepNumber: { type: Number, default: 1 },
        connectionMethod: { type: String, required: true },
        wifiHost: { type: String, default: "" },
        selectedProduct: { type: Object, default: null },
        selectedModel: { type: Object, default: null },
        products: { type: Array, required: true },
        capabilities: { type: Object, required: true },
        isEnteringDfuMode: { type: Boolean, default: false },
    },
    emits: [
        "update:connectionMethod",
        "update:wifiHost",
        "update:selectedProduct",
        "update:selectedModel",
        "enter-dfu",
    ],
    computed: {
        connectionOptions() {
            const t = this.capabilities?.transports || {};
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
        },
    },
    methods: {
        onProductChange(event) {
            const id = event.target.value;
            const product = this.products.find((p) => String(p.id) === String(id)) || null;
            this.$emit("update:selectedProduct", product);
            this.$emit("update:selectedModel", null);
        },
        onModelChange(event) {
            const id = event.target.value;
            const model = this.selectedProduct?.models?.find((m) => String(m.id) === String(id)) || null;
            this.$emit("update:selectedModel", model);
        },
    },
};
</script>

<style scoped>
.rnf-label {
    @apply text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider;
}
.rnf-input {
    @apply w-full bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all;
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
