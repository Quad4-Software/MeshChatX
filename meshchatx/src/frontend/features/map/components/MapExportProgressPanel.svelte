<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        status: { status?: string; progress?: number; current?: number; total?: number; error?: string };
        exportId?: string | number | null;
        onDismiss?: () => void;
        onCancel?: () => void;
        onShowOfflineMaps?: () => void;
    }

    let { status, exportId = null, onDismiss, onCancel, onShowOfflineMaps }: Props = $props();
</script>

<div
    class="absolute bottom-4 right-4 z-20 w-72 bg-sem-surface rounded-xl shadow-2xl border border-sem-border p-4 space-y-3 animate-in slide-in-from-bottom-4"
>
    <div class="flex justify-between items-center">
        <span class="font-bold text-sm text-sem-fg">
            {status.status === "completed" ? t("map.download_ready") : t("map.exporting")}
        </span>
        {#if status.status === "completed" || status.status === "failed"}
            <button type="button" class="text-gray-400 hover:text-sem-fg cursor-pointer" onclick={() => onDismiss?.()}>
                <MaterialDesignIcon iconName="close" class="size-4" />
            </button>
        {:else}
            <button
                type="button"
                class="text-xs font-bold text-red-500 hover:text-red-600 uppercase tracking-tighter cursor-pointer"
                onclick={() => onCancel?.()}
            >
                {t("common.cancel")}
            </button>
        {/if}
    </div>

    {#if status.status !== "completed" && status.status !== "failed"}
        <div>
            <div class="w-full h-2 bg-sem-surface-muted rounded-full overflow-hidden">
                <div
                    class="h-full bg-blue-500 transition-all duration-300"
                    style="width: {status.progress || 0}%;"
                ></div>
            </div>
            <div class="flex justify-between text-[10px] text-gray-500 mt-1 uppercase font-bold tracking-wider">
                <span>{status.current || 0} / {status.total || 0} tiles</span>
                <span>{status.progress || 0}%</span>
            </div>
        </div>
    {/if}

    {#if status.status === "completed"}
        <div class="flex flex-col gap-2">
            <a
                href="/api/v1/map/export/{exportId}/download"
                class="flex items-center justify-center space-x-2 w-full py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-bold transition-colors shadow-md text-xs"
            >
                <MaterialDesignIcon iconName="download" class="size-4" />
                <span>{t("map.download_now")}</span>
            </a>
            <button
                type="button"
                class="flex items-center justify-center space-x-2 w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-bold transition-colors shadow-md text-xs cursor-pointer"
                onclick={() => onShowOfflineMaps?.()}
            >
                <MaterialDesignIcon iconName="map-check" class="size-4" />
                <span>Show in Offline Maps</span>
            </button>
        </div>
    {/if}

    {#if status.status === "failed"}
        <div class="text-xs text-red-500 bg-red-50 dark:bg-red-950/20 p-2 rounded-lg">
            {status.error}
        </div>
    {/if}
</div>
