<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { formatBytesPerSecond } from "../lib/nomadPageDownloads.js";

    interface Props {
        isDownloading?: boolean;
        filePath?: string | null;
        progress?: number;
        downloadSpeed?: number | null;
        oncancel?: () => void;
    }

    let { isDownloading = false, filePath = null, progress = 0, downloadSpeed = null, oncancel }: Props = $props();
</script>

{#if isDownloading}
    <div class="flex w-full border-sem-border border-t p-2 bg-sem-surface text-sem-fg">
        <div class="my-auto mr-2">
            <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
            </svg>
        </div>
        <div class="my-auto flex-1 text-sm truncate">
            Downloading: {filePath} ({progress}%)
            {#if downloadSpeed !== null}
                <span class="ml-2 text-xs text-sem-fg-muted">
                    - {formatBytesPerSecond(downloadSpeed)}
                </span>
            {/if}
        </div>
        <button
            type="button"
            class="my-auto text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 rounded px-3 py-1 text-sm font-semibold cursor-pointer"
            onclick={() => oncancel?.()}
        >
            {t("common.cancel")}
        </button>
    </div>
{/if}
