<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        offlineEnabled?: boolean;
        cachingEnabled?: boolean;
        mbtilesList?: any[];
        mbtilesDir?: string;
        hasOfflineMap?: boolean;
        onToggleOffline?: (val: boolean) => void;
        onToggleCaching?: (val: boolean) => void;
        onUpload?: () => void;
        onSetActive?: (name: string) => void;
        onDeleteFile?: (name: string) => void;
        onSaveDir?: (dir: string) => void;
        onClearCache?: () => void;
        onExportRegion?: () => void;
        onRestoreStarter?: () => void;
    }

    let {
        offlineEnabled = false,
        cachingEnabled = true,
        mbtilesList = [],
        mbtilesDir = "",
        hasOfflineMap = false,
        onToggleOffline,
        onToggleCaching,
        onUpload,
        onSetActive,
        onDeleteFile,
        onSaveDir,
        onClearCache,
        onExportRegion,
        onRestoreStarter,
    }: Props = $props();
</script>

<div class="space-y-3">
    <div class="flex items-center bg-sem-surface-muted rounded-lg p-0.5">
        <button
            type="button"
            class="flex-1 px-2 py-1.5 text-[11px] font-medium rounded-md cursor-pointer {!offlineEnabled
                ? 'bg-white dark:bg-zinc-700 text-blue-600'
                : 'text-gray-500'}"
            onclick={() => onToggleOffline?.(false)}
        >
            {t("map.online_mode")}
        </button>
        <button
            type="button"
            class="flex-1 px-2 py-1.5 text-[11px] font-medium rounded-md cursor-pointer {offlineEnabled
                ? 'bg-white dark:bg-zinc-700 text-blue-600'
                : 'text-gray-500'}"
            onclick={() => onToggleOffline?.(true)}
        >
            {t("map.offline_mode")}
        </button>
    </div>
    <label class="flex items-center justify-between text-[11px] text-sem-fg-muted cursor-pointer">
        <span>{t("map.caching_enabled")}</span>
        <input
            type="checkbox"
            checked={cachingEnabled}
            onchange={(e) => onToggleCaching?.((e.target as HTMLInputElement).checked)}
        />
    </label>
    <button
        type="button"
        class="w-full py-2 text-[10px] font-semibold uppercase rounded-lg bg-blue-500 text-white cursor-pointer"
        onclick={() => onUpload?.()}
    >
        {t("map.upload_mbtiles")}
    </button>
    {#if offlineEnabled && !hasOfflineMap}
        <div class="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 space-y-2">
            <div class="text-[11px] text-sem-fg leading-snug">{t("map.offline_empty_hint")}</div>
            <button
                type="button"
                class="w-full py-1.5 text-[10px] font-semibold uppercase rounded-lg border border-sem-border cursor-pointer"
                onclick={() => onRestoreStarter?.()}
            >
                {t("map.restore_starter_tiles")}
            </button>
        </div>
    {/if}
    {#if offlineEnabled && hasOfflineMap}
        <p class="text-[10px] text-sem-fg-muted leading-snug">
            {t("map.starter_attribution")}
        </p>
    {/if}
    <button
        type="button"
        class="w-full py-2 text-[10px] font-semibold uppercase rounded-lg border border-sem-border cursor-pointer"
        onclick={() => onExportRegion?.()}
    >
        {t("map.data_export_region")}
    </button>
    <button
        type="button"
        class="w-full py-2 text-[10px] font-semibold uppercase rounded-lg border border-sem-border cursor-pointer"
        onclick={() => onClearCache?.()}
    >
        {t("map.clear_cache")}
    </button>
    <label class="block text-[11px] text-sem-fg-muted space-y-1">
        <span>{t("map.storage_path")}</span>
        <input
            value={mbtilesDir}
            type="text"
            class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] font-mono text-sem-fg"
            onblur={(e) => onSaveDir?.((e.target as HTMLInputElement).value)}
        />
    </label>
    {#each mbtilesList as file (file.name)}
        <div class="flex items-center justify-between rounded-lg border border-sem-border p-2">
            <div class="min-w-0">
                <div class="text-[11px] font-semibold truncate text-sem-fg">{file.name}</div>
                <div class="text-[9px] text-gray-500">{((file.size || 0) / 1024 / 1024).toFixed(1)} MB</div>
            </div>
            <div class="flex items-center gap-1">
                {#if !file.is_active}
                    <button
                        type="button"
                        class="p-1 text-blue-500 cursor-pointer text-xs"
                        onclick={() => onSetActive?.(file.name)}
                    >
                        {t("map.set_active")}
                    </button>
                {/if}
                <button
                    type="button"
                    class="p-1 text-red-500 cursor-pointer text-xs"
                    onclick={() => onDeleteFile?.(file.name)}
                >
                    {t("map.delete")}
                </button>
            </div>
        </div>
    {/each}
</div>
