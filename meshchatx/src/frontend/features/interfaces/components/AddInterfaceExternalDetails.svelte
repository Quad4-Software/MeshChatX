<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toggle from "./Toggle.svelte";
    import type { InterfaceModule } from "../lib/types.js";

    interface Props {
        customTypeName: string;
        customOptionsJson: string;
        installedModules?: InterfaceModule[];
        modulesPath?: string;
        overwrite?: boolean;
        isBusy?: boolean;
        oncustomtypenamechange?: (val: string) => void;
        oncustomoptionsjsonchange?: (val: string) => void;
        onoverwritechange?: (val: boolean) => void;
        onuploadmodule?: (file: File) => void;
        ondeletemodule?: (typeName: string) => void;
    }

    let {
        customTypeName = "",
        customOptionsJson = "{}",
        installedModules = [],
        modulesPath = "",
        overwrite = false,
        isBusy = false,
        oncustomtypenamechange,
        oncustomoptionsjsonchange,
        onoverwritechange,
        onuploadmodule,
        ondeletemodule,
    }: Props = $props();

    let fileInputRef: HTMLInputElement | null = $state(null);

    function handleFileSelected(e: Event) {
        const input = e.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            onuploadmodule?.(file);
            input.value = "";
        }
    }
</script>

<div class="space-y-4">
    <div class="p-3 bg-amber-500/10 border border-amber-500/20 rounded-2xl text-xs text-amber-700 dark:text-amber-300">
        <div class="font-semibold">External Python Interface Module</div>
        <p class="mt-0.5 opacity-80">Loads custom Reticulum interface drivers installed in the RNS interfacepath.</p>
        {#if modulesPath}
            <div class="mt-1 font-mono text-[10px] break-all opacity-70">Path: {modulesPath}</div>
        {/if}
    </div>

    <div>
        <label for="ext-type-name" class="glass-label block font-medium mb-1">Custom Interface Class / Type</label>
        <input
            id="ext-type-name"
            value={customTypeName}
            type="text"
            placeholder="e.g. CustomEthernetInterface"
            class="input-field"
            oninput={(e) => oncustomtypenamechange?.((e.target as HTMLInputElement).value)}
        />
    </div>

    <div>
        <label for="ext-options-json" class="glass-label block font-medium mb-1">Interface Parameters (JSON)</label>
        <textarea
            id="ext-options-json"
            value={customOptionsJson}
            rows={4}
            placeholder={`{\n  "device": "/dev/spidev0.0",\n  "speed": 10000000\n}`}
            class="input-field font-mono text-xs"
            oninput={(e) => oncustomoptionsjsonchange?.((e.target as HTMLTextAreaElement).value)}></textarea>
    </div>

    <!-- Upload Module Section -->
    <div class="p-3 bg-sem-surface border border-sem-border rounded-xl space-y-3">
        <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-sem-fg">Install Custom Interface (.py)</span>
            <div class="flex items-center gap-2">
                <Toggle id="ext-overwrite" checked={overwrite} onchange={(val) => onoverwritechange?.(val)} />
                <label for="ext-overwrite" class="cursor-pointer mb-0! text-[10px] text-sem-fg-muted">Overwrite</label>
            </div>
        </div>
        <input bind:this={fileInputRef} type="file" accept=".py" class="hidden" onchange={handleFileSelected} />
        <button
            type="button"
            class="secondary-chip text-xs py-1.5! px-3!"
            disabled={isBusy}
            onclick={() => fileInputRef?.click()}
        >
            <MaterialDesignIcon iconName="upload" class="w-3.5 h-3.5" />
            <span>Upload Interface Module (.py)</span>
        </button>

        {#if installedModules.length > 0}
            <div class="pt-2 border-t border-sem-border space-y-1.5">
                <div class="text-[10px] uppercase font-bold text-sem-fg-muted">Installed Custom Modules</div>
                <div class="flex flex-wrap gap-1.5">
                    {#each installedModules as mod (mod.name)}
                        <div
                            class="inline-flex items-center gap-1.5 bg-sem-surface-muted px-2.5 py-1 rounded-lg text-xs font-mono"
                        >
                            <span>{mod.name}</span>
                            <button
                                type="button"
                                class="text-red-500 hover:text-red-700"
                                onclick={() => mod.name && ondeletemodule?.(mod.name)}
                            >
                                <MaterialDesignIcon iconName="close-circle" class="w-3.5 h-3.5" />
                            </button>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </div>
</div>
