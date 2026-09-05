<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import RNodeDeviceSelector from "./RNodeDeviceSelector.svelte";
    import RNodeFirmwareSelector from "./RNodeFirmwareSelector.svelte";
    import RNodeFlashAction from "./RNodeFlashAction.svelte";

    interface Props {
        connectionMethod: string;
        wifiHost: string;
        selectedProduct: any;
        selectedModel: any;
        firmwareFile: File | null;
        products: any;
        capabilities: any;
        isEnteringDfuMode: boolean;
        canFlash: boolean;
        isFlashing: boolean;
        flashingProgress: number;
        flashingStatus: string;
        flashError: string | null;
        onenterDfu: () => void;
        onflash: () => void;
    }

    let {
        connectionMethod = $bindable(),
        wifiHost = $bindable(),
        selectedProduct = $bindable(),
        selectedModel = $bindable(),
        firmwareFile = $bindable(),
        products,
        capabilities,
        isEnteringDfuMode,
        canFlash,
        isFlashing,
        flashingProgress,
        flashingStatus,
        flashError,
        onenterDfu,
        onflash,
    }: Props = $props();
</script>

<div class="border border-sem-border bg-sem-surface rounded-lg overflow-hidden">
    <div class="grid grid-cols-1 md:grid-cols-2">
        <div class="p-4 sm:p-6 border-b md:border-b-0 md:border-r border-sem-border">
            <RNodeDeviceSelector
                stepNumber={1}
                bind:connectionMethod
                bind:wifiHost
                bind:selectedProduct
                bind:selectedModel
                {products}
                {capabilities}
                {isEnteringDfuMode}
                {onenterDfu}
            />
        </div>
        <div class="p-4 sm:p-6 bg-gray-50/50 dark:bg-zinc-900/50">
            <RNodeFirmwareSelector stepNumber={2} bind:firmwareFile />
            <div class="mt-4">
                <RNodeFlashAction
                    {canFlash}
                    {isFlashing}
                    {flashingProgress}
                    {flashingStatus}
                    errorMessage={flashError}
                    {onflash}
                />
            </div>
        </div>
    </div>
</div>
