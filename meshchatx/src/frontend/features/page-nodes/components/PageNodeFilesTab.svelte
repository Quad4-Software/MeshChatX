<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatFileSize } from "../lib/pageNodesFormat.js";
    import type { PageNodeFileItem } from "../lib/types.js";

    interface Props {
        files: PageNodeFileItem[];
        onUploadFile: (file: File) => void;
        onDeleteFile: (fileName: string) => void;
    }

    let { files, onUploadFile, onDeleteFile }: Props = $props();

    let fileInput: HTMLInputElement | null = null;

    function triggerFileInput() {
        fileInput?.click();
    }

    function handleFileSelected(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;
        onUploadFile(file);
        target.value = "";
    }
</script>

<div class="space-y-3">
    <div class="flex gap-2">
        <input bind:this={fileInput} type="file" class="hidden" onchange={handleFileSelected} />
        <button type="button" class="primary-chip py-1! px-3! text-xs!" onclick={triggerFileInput}>
            <MaterialDesignIcon iconName="upload" class="w-3.5 h-3.5" />
            {t("tools.mesh_server.upload_file")}
        </button>
    </div>

    {#if files.length === 0}
        <div class="text-sm text-sem-fg-muted py-4 text-center">
            {t("tools.mesh_server.no_files")}
        </div>
    {/if}

    {#each files as file (file.name)}
        <div
            class="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-sem-border"
        >
            <div class="flex items-center gap-2">
                <MaterialDesignIcon iconName="file-outline" class="w-4 h-4 text-blue-500" />
                <span class="text-sm font-mono text-sem-fg">{file.name}</span>
                <span class="text-xs text-sem-fg-muted">{formatFileSize(file.size)}</span>
            </div>
            <button
                type="button"
                class="secondary-chip py-0.5! px-2! text-xs! text-red-500!"
                onclick={() => onDeleteFile(file.name)}
            >
                <MaterialDesignIcon iconName="delete" class="w-3 h-3" />
            </button>
        </div>
    {/each}
</div>
