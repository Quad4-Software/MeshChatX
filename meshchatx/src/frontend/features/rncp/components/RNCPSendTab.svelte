<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ElectronUtils from "../../../js/ElectronUtils.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        destinationHash?: string;
        filePath?: string;
        timeout?: number;
        noCompress?: boolean;
        inProgress?: boolean;
        progress?: number;
        result?: { success: boolean; message: string; filePath?: string } | null;
        onsend?: () => void;
        oncancel?: () => void;
        onopenpath?: (path: string) => void;
    }

    let {
        destinationHash = $bindable(""),
        filePath = $bindable(""),
        timeout = $bindable(30),
        noCompress = $bindable(false),
        inProgress = false,
        progress = 0,
        result = null,
        onsend,
        oncancel,
        onopenpath,
    }: Props = $props();

    let fileInputRef = $state<HTMLInputElement | null>(null);

    async function pickSendFile(): Promise<void> {
        const picked = await ElectronUtils.pickFile();
        if (picked) {
            filePath = picked;
            return;
        }
        fileInputRef?.click();
    }

    function onWebSendFilePicked(event: Event): void {
        const target = event.target as HTMLInputElement | null;
        const file = target?.files?.[0];
        if (target) {
            target.value = "";
        }
        if (!file) {
            return;
        }
        filePath = "";
        DialogUtils.alert(t("rncp.web_path_hint"));
    }
</script>

<div class="space-y-4">
    <div class="grid lg:grid-cols-2 gap-4">
        <div>
            <label class="glass-label" for="rncp-send-dest">{t("rncp.destination_hash")}</label>
            <input
                id="rncp-send-dest"
                bind:value={destinationHash}
                type="text"
                placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                class="input-field font-mono"
            />
        </div>
        <div>
            <label class="glass-label" for="rncp-send-path">{t("rncp.file_path")}</label>
            <div class="flex gap-2">
                <input
                    id="rncp-send-path"
                    bind:value={filePath}
                    type="text"
                    placeholder="/path/to/file"
                    class="input-field flex-1 min-w-0"
                />
                <input bind:this={fileInputRef} type="file" class="hidden" onchange={onWebSendFilePicked} />
                <button
                    type="button"
                    class="secondary-chip px-3 py-2 text-xs shrink-0 cursor-pointer"
                    title={t("rncp.browse_file")}
                    onclick={pickSendFile}
                >
                    <MaterialDesignIcon iconName="folder-open-outline" class="w-4 h-4" />
                    {t("rncp.browse_file")}
                </button>
            </div>
        </div>
    </div>
    <div class="grid lg:grid-cols-2 gap-4">
        <div>
            <label class="glass-label" for="rncp-send-timeout">{t("rncp.timeout_seconds")}</label>
            <input id="rncp-send-timeout" bind:value={timeout} type="number" min="1" class="input-field" />
        </div>
        <div class="flex items-end">
            <label class="flex items-center gap-2 cursor-pointer">
                <input bind:checked={noCompress} type="checkbox" class="rounded-sm" />
                <span class="text-sm text-gray-700 dark:text-gray-300">{t("rncp.disable_compression")}</span>
            </label>
        </div>
    </div>
    <div class="flex gap-2">
        {#if !inProgress}
            <button type="button" class="primary-chip px-4 py-2 text-sm cursor-pointer" onclick={onsend}>
                <MaterialDesignIcon iconName="upload" class="w-4 h-4" />
                {t("rncp.send_file")}
            </button>
        {:else}
            <button
                type="button"
                class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50 cursor-pointer"
                onclick={oncancel}
            >
                <MaterialDesignIcon iconName="close" class="w-4 h-4" />
                {t("rncp.cancel")}
            </button>
        {/if}
    </div>
    {#if progress > 0}
        <div class="space-y-2">
            <div class="flex justify-between text-sm">
                <span class="text-gray-700 dark:text-gray-300">{t("rncp.progress")}</span>
                <span class="text-gray-700 dark:text-gray-300">{Math.round(progress * 100)}%</span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-2">
                <div class="bg-blue-600 h-2 rounded-full transition-all" style="width: {progress * 100}%"></div>
            </div>
        </div>
    {/if}
    {#if result}
        <div
            class="p-3 rounded-lg space-y-2 {result.success
                ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}"
        >
            <div>{result.message}</div>
            {#if result.success && result.filePath}
                <div class="font-mono text-xs break-all">
                    {result.filePath}
                </div>
                <div class="flex gap-2">
                    <button
                        type="button"
                        class="secondary-chip text-xs py-1 px-2 cursor-pointer"
                        onclick={() => onopenpath?.(result?.filePath || "")}
                    >
                        {t("rncp.show_in_folder")}
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    .glass-label {
        display: block;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
</style>
