<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        canFlash?: boolean;
        isFlashing?: boolean;
        flashingProgress?: number;
        flashingStatus?: string;
        errorMessage?: string | null;
        onflash?: () => void;
    }

    let {
        canFlash = false,
        isFlashing = false,
        flashingProgress = 0,
        flashingStatus = "",
        errorMessage = null,
        onflash,
    }: Props = $props();
</script>

<div class="space-y-3">
    {#if errorMessage}
        <div
            class="flex items-start gap-2 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
            role="alert"
        >
            <MaterialDesignIcon iconName="alert-circle" class="size-4 mt-0.5 text-red-600 dark:text-red-400 shrink-0" />
            <span class="text-xs text-red-600 dark:text-red-400 wrap-break-word">{errorMessage}</span>
        </div>
    {/if}

    <button
        type="button"
        disabled={!canFlash || isFlashing}
        data-testid="rnode-flash-btn"
        class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-green-600 hover:bg-green-700 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-green-600/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        onclick={() => onflash?.()}
    >
        {#if isFlashing}
            <MaterialDesignIcon iconName="loading" class="size-4 animate-spin text-white" />
        {:else}
            <MaterialDesignIcon iconName="flash" class="size-5" />
        {/if}
        <span>
            {isFlashing
                ? t("tools.rnode_flasher.flashing", { percentage: flashingProgress })
                : t("tools.rnode_flasher.flash_now")}
        </span>
    </button>

    {#if isFlashing}
        <div class="space-y-1.5 pt-1" role="status" aria-live="polite">
            <div class="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-zinc-800">
                <div
                    class="h-full rounded-full bg-green-600 transition-[width]"
                    style="width: {flashingProgress}%"
                ></div>
            </div>
            <div class="flex items-center justify-between text-[10px] font-mono">
                <span class="text-sem-fg-muted truncate">{flashingStatus}</span>
                <span class="text-sem-fg-muted font-bold">{flashingProgress}%</span>
            </div>
        </div>
    {/if}
</div>
