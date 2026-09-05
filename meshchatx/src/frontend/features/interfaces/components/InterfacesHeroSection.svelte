<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        hasPendingChanges?: boolean;
        isElectron?: boolean;
        reloadingRns?: boolean;
        searchTerm?: string;
        typeFilter?: string;
        sortedInterfaceTypes?: string[];
        onrelaunch?: () => void;
        onadd?: () => void;
        onimport?: () => void;
        onexportall?: () => void;
        onreloadrns?: () => void;
        onsearchchange?: (v: string) => void;
        ontypechange?: (v: string) => void;
    }

    let {
        hasPendingChanges = false,
        isElectron = false,
        reloadingRns = false,
        searchTerm = "",
        typeFilter = "all",
        sortedInterfaceTypes = [],
        onrelaunch,
        onadd,
        onimport,
        onexportall,
        onreloadrns,
        onsearchchange,
        ontypechange,
    }: Props = $props();
</script>

<!-- Restart Reminder Banner -->
{#if hasPendingChanges}
    <div
        class="bg-amber-600 text-white border border-amber-500/30 p-4 sm:rounded-xl flex flex-wrap gap-3 items-center mb-3 sm:mb-4"
    >
        <div class="flex items-center gap-3">
            <MaterialDesignIcon iconName="alert" class="w-6 h-6 shrink-0" />
            <div>
                <div class="text-lg font-semibold">{t("interfaces.restart_required")}</div>
                <div class="text-sm">{t("interfaces.restart_description")}</div>
            </div>
        </div>
        {#if isElectron}
            <button
                type="button"
                class="ml-auto inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-sm font-bold text-amber-600 hover:bg-white/90 transition shadow-xs"
                onclick={onrelaunch}
            >
                <MaterialDesignIcon iconName="restart" class="w-4 h-4" />
                <span>{t("interfaces.restart_now")}</span>
            </button>
        {/if}
    </div>
{/if}

<!-- Hero Section -->
<div
    class="interfaces-section interfaces-section--hero flex flex-col lg:flex-row lg:items-center justify-between gap-4"
>
    <div class="space-y-3 flex-1 min-w-0">
        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
            {t("interfaces.manage")}
        </div>
        <div class="text-3xl font-black text-sem-fg tracking-tight">
            {t("interfaces.title")}
        </div>
        <div class="text-sm text-sem-fg-muted leading-relaxed max-w-xl">
            {t("interfaces.description")}
        </div>
        <div class="flex flex-wrap gap-2 pt-2">
            <button
                type="button"
                class="primary-chip px-4 py-2 text-sm min-h-[44px] sm:min-h-0 items-center justify-center hidden sm:inline-flex"
                onclick={onadd}
            >
                <MaterialDesignIcon iconName="plus" class="w-4 h-4" />
                <span>{t("interfaces.add_interface")}</span>
            </button>
            <button type="button" class="secondary-chip text-sm" onclick={onimport}>
                <MaterialDesignIcon iconName="import" class="w-4 h-4" />
                <span>{t("interfaces.import")}</span>
            </button>
            <button type="button" class="secondary-chip text-sm" onclick={onexportall}>
                <MaterialDesignIcon iconName="export" class="w-4 h-4" />
                <span>{t("interfaces.export_all")}</span>
            </button>
            <button
                type="button"
                class="secondary-chip text-sm transition-shadow {hasPendingChanges
                    ? 'ring-2 ring-amber-400 shadow-lg shadow-amber-500/40 animate-pulse motion-reduce:animate-none'
                    : ''}"
                disabled={reloadingRns}
                onclick={onreloadrns}
            >
                <MaterialDesignIcon iconName="restart" class="w-4 h-4 {reloadingRns ? 'animate-spin' : ''}" />
                <span>{reloadingRns ? t("app.reloading_rns") : "Restart RNS"}</span>
            </button>
        </div>
    </div>

    <div class="w-full md:w-96 shrink-0 space-y-4">
        <div class="relative group">
            <MaterialDesignIcon
                iconName="magnify"
                class="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-sem-accent transition-colors"
            />
            <input
                value={searchTerm}
                oninput={(e) => onsearchchange?.((e.target as HTMLInputElement).value)}
                type="text"
                placeholder={t("interfaces.search_placeholder")}
                class="w-full pl-12 pr-4 py-3 bg-sem-surface border border-sem-border rounded-xl focus:outline-hidden focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 text-sem-fg placeholder:text-sem-fg-muted shadow-xs"
            />
            {#if searchTerm}
                <button
                    type="button"
                    class="absolute inset-y-0 right-0 pr-4 flex items-center text-sem-fg-muted hover:text-sem-fg"
                    onclick={() => onsearchchange?.("")}
                >
                    <MaterialDesignIcon iconName="close-circle" class="w-5 h-5" />
                </button>
            {/if}
        </div>
        <div>
            <select
                value={typeFilter}
                onchange={(e) => ontypechange?.((e.target as HTMLSelectElement).value)}
                class="w-full px-4 py-2.5 bg-sem-surface border border-sem-border rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500/50 text-sem-fg"
            >
                <option value="all">{t("interfaces.all_types")}</option>
                {#each sortedInterfaceTypes as type (type)}
                    <option value={type}>{type}</option>
                {/each}
            </select>
        </div>
    </div>
</div>
