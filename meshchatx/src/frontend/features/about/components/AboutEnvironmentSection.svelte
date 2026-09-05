<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { AppInfo } from "../lib/types.js";

    interface Props {
        appInfo?: AppInfo | null;
        isElectron?: boolean;
        onshowreticulumconfig?: () => void;
        onshowdatabase?: () => void;
    }

    let { appInfo = null, isElectron = false, onshowreticulumconfig, onshowdatabase }: Props = $props();
</script>

{#if appInfo}
    <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0">
        <div class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
            <MaterialDesignIcon iconName="server" class="size-3.5" />
            {t("about.environment_information")}
        </div>
        <div class="grid gap-8 sm:grid-cols-2 text-sm min-w-0">
            <div>
                <div class="text-[10px] font-black uppercase tracking-[0.2em] mb-2 opacity-50">
                    {t("about.reticulum_config")}
                </div>
                <div
                    class="bg-zinc-50 dark:bg-zinc-950 break-all text-[11px] p-3 rounded-xl border border-zinc-100 dark:border-zinc-800 font-mono"
                >
                    {appInfo.reticulum_config_path || t("about.path_unknown")}
                </div>
                {#if isElectron}
                    <button
                        type="button"
                        class="secondary-chip mt-3 px-3 py-1 text-[10px]"
                        onclick={onshowreticulumconfig}
                    >
                        <MaterialDesignIcon iconName="folder-open" class="size-3.5 shrink-0" />
                        {t("about.reveal_config_file")}
                    </button>
                {/if}
            </div>
            <div>
                <div class="text-[10px] font-black uppercase tracking-[0.2em] mb-2 opacity-50">
                    {t("about.database_path")}
                </div>
                <div
                    class="bg-zinc-50 dark:bg-zinc-950 break-all text-[11px] p-3 rounded-xl border border-zinc-100 dark:border-zinc-800 font-mono"
                >
                    {appInfo.database_path || t("about.path_unknown")}
                </div>
                {#if isElectron}
                    <button type="button" class="secondary-chip mt-3 px-3 py-1 text-[10px]" onclick={onshowdatabase}>
                        <MaterialDesignIcon iconName="database-search" class="size-3.5 shrink-0" />
                        {t("about.reveal_database_file")}
                    </button>
                {/if}
            </div>
        </div>
    </div>
{/if}
