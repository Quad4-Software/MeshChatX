<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        stepNumber?: number;
        connectionMethod: string;
        wifiHost?: string;
        selectedProduct?: any;
        selectedModel?: any;
        products: any[];
        capabilities: any;
        isEnteringDfuMode?: boolean;
        onenterDfu?: () => void;
    }

    let {
        stepNumber = 1,
        connectionMethod = $bindable(),
        wifiHost = $bindable(""),
        selectedProduct = $bindable(null),
        selectedModel = $bindable(null),
        products,
        capabilities,
        isEnteringDfuMode = false,
        onenterDfu,
    }: Props = $props();

    let connectionOptions = $derived.by(() => {
        const tr = capabilities?.transports || {};
        return [
            {
                id: "serial",
                labelKey: "tools.rnode_flasher.serial",
                icon: "usb-port",
                available: Boolean(tr.serial?.available),
            },
            {
                id: "bluetooth",
                labelKey: "tools.rnode_flasher.bluetooth",
                icon: "bluetooth",
                available: Boolean(tr.bluetooth?.available),
            },
            {
                id: "wifi",
                labelKey: "tools.rnode_flasher.wifi",
                icon: "wifi",
                available: Boolean(tr.wifi?.available),
            },
        ];
    });

    function onProductChange(event: Event): void {
        const target = event.target as HTMLSelectElement;
        const id = target.value;
        selectedProduct = products.find((p) => String(p.id) === String(id)) || null;
        selectedModel = null;
    }

    function onModelChange(event: Event): void {
        const target = event.target as HTMLSelectElement;
        const id = target.value;
        selectedModel = selectedProduct?.models?.find((m: any) => String(m.id) === String(id)) || null;
    }
</script>

<div class="space-y-4">
    <div class="flex items-center gap-2">
        <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-sem-accent shrink-0">
            <MaterialDesignIcon iconName="usb-port" class="size-5" />
        </div>
        <h2 class="font-bold text-sem-fg">{stepNumber}. {t("tools.rnode_flasher.select_device")}</h2>
    </div>

    <div class="space-y-1">
        <label
            class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wider block"
            for="rnf-connection-method"
        >
            {t("tools.rnode_flasher.connection_method")}
        </label>
        <div id="rnf-connection-method" class="grid grid-cols-3 gap-2">
            {#each connectionOptions as option (option.id)}
                <button
                    type="button"
                    data-testid={`rnode-transport-${option.id}`}
                    disabled={!option.available}
                    class="flex flex-col items-center justify-center gap-1 py-2.5 px-2 rounded-xl border text-xs sm:text-sm font-bold transition-all cursor-pointer disabled:cursor-not-allowed {connectionMethod ===
                    option.id
                        ? 'bg-blue-600 text-white border-blue-600'
                        : option.available
                          ? 'bg-gray-50 dark:bg-zinc-800/50 border-sem-border text-sem-fg-muted hover:bg-sem-surface-muted'
                          : 'bg-sem-surface-muted border-sem-border text-gray-400 dark:text-zinc-600'}"
                    onclick={() => {
                        if (option.available) {
                            connectionMethod = option.id;
                        }
                    }}
                >
                    <MaterialDesignIcon iconName={option.icon} class="size-4 sm:size-5" />
                    <span>{t(option.labelKey)}</span>
                </button>
            {/each}
        </div>
    </div>

    {#if connectionMethod === "wifi"}
        <div class="space-y-1">
            <label class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wider block" for="rnf-wifi-host"
                >{t("tools.rnode_flasher.ip_address")}</label
            >
            <input
                id="rnf-wifi-host"
                bind:value={wifiHost}
                type="text"
                inputmode="decimal"
                autocomplete="off"
                spellcheck="false"
                class="w-full bg-gray-50 dark:bg-zinc-800/50 border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all"
                placeholder={t("tools.rnode_flasher.ip_address_placeholder")}
            />
            <p class="text-[10px] text-sem-fg-muted">
                {t("tools.rnode_flasher.wifi_help")}
            </p>
        </div>
    {/if}

    <div class="space-y-1">
        <label class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wider block" for="rnf-product-select">
            {t("tools.rnode_flasher.product")}
        </label>
        <select
            id="rnf-product-select"
            value={selectedProduct?.id ?? ""}
            class="rnf-select w-full bg-gray-50 dark:bg-zinc-800/50 border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all"
            onchange={onProductChange}
        >
            <option value="" disabled>{t("tools.rnode_flasher.select_product")}</option>
            {#each products as product, idx (`${product.id ?? ""}-${idx}`)}
                <option value={product.id}>
                    {product.name}
                </option>
            {/each}
        </select>
    </div>

    <div class="space-y-1">
        <label class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wider block" for="rnf-model-select">
            {t("tools.rnode_flasher.model")}
        </label>
        <select
            id="rnf-model-select"
            value={selectedModel?.id ?? ""}
            disabled={!selectedProduct}
            class="rnf-select w-full bg-gray-50 dark:bg-zinc-800/50 border border-sem-border text-sem-fg text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all disabled:opacity-50"
            onchange={onModelChange}
        >
            <option value="" disabled>{t("tools.rnode_flasher.select_model")}</option>
            {#if selectedProduct && Array.isArray(selectedProduct.models)}
                {#each selectedProduct.models as model, idx (`${model.id ?? ""}-${idx}`)}
                    <option value={model.id}>
                        {model.name}
                    </option>
                {/each}
            {/if}
        </select>
    </div>

    {#if selectedProduct?.platform === 0x70 && connectionMethod === "serial"}
        <button
            type="button"
            disabled={isEnteringDfuMode}
            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/40 px-4 py-2.5 text-sm font-bold text-amber-700 dark:text-amber-400 transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
            onclick={() => onenterDfu?.()}
        >
            {#if isEnteringDfuMode}
                <MaterialDesignIcon iconName="loading" class="size-4 animate-spin text-amber-700 dark:text-amber-400" />
            {:else}
                <MaterialDesignIcon iconName="restart-alert" class="size-4" />
            {/if}
            <span>
                {isEnteringDfuMode
                    ? t("tools.rnode_flasher.entering_dfu_mode")
                    : t("tools.rnode_flasher.enter_dfu_mode")}
            </span>
        </button>
    {/if}
</div>

<style>
    select.rnf-select {
        appearance: none;
        background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
        background-position: right 0.5rem center;
        background-repeat: no-repeat;
        background-size: 1.5em 1.5em;
        padding-right: 2.5rem;
    }
</style>
