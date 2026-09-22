<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { MESHCHATX_LOGO_URL, RETICULUM_LOGO_URL } from "../lib/constants.js";
    import type { DocSection, DocsActiveTab, DocsStatus } from "../lib/types.js";

    interface Props {
        activeTab: DocsActiveTab;
        status: DocsStatus;
        searchQuery: string;
        isSearching: boolean;
        visibleDocSections: DocSection[];
        selectedDocPath: string | null;
        onTabChange: (tab: DocsActiveTab) => void;
        onSearchInput: (value: string) => void;
        onClearSearch: () => void;
        onSelectDoc: (path: string) => void;
        onExportDocs: () => void;
        onZipUpload: (event: Event) => void;
    }

    let {
        activeTab,
        status,
        searchQuery = $bindable(),
        isSearching,
        visibleDocSections,
        selectedDocPath,
        onTabChange,
        onSearchInput,
        onClearSearch,
        onSelectDoc,
        onExportDocs,
        onZipUpload,
    }: Props = $props();
</script>

<div class="lg:hidden p-3 border-b border-sem-border bg-sem-surface space-y-2 shrink-0 z-20">
    <div class="flex items-center gap-2">
        <a
            href="#/tools"
            class="inline-flex items-center justify-center gap-0.5 rounded-lg pl-0 pr-1.5 py-1.5 min-h-9 min-w-9 text-sm font-medium text-sem-fg-muted hover:bg-sem-surface-muted transition-colors shrink-0"
            aria-label={t("tools.back_to_tools")}
        >
            <MaterialDesignIcon iconName="chevron-left" class="size-6 shrink-0" />
            <span class="hidden sm:inline truncate max-w-[8rem]">{t("app.tools")}</span>
        </a>
        <div class="flex items-center gap-1 ml-auto shrink-0">
            {#if status.has_docs || status.has_meshchatx_docs}
                <button
                    type="button"
                    class="p-1.5 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors"
                    title="Export all documentation as ZIP"
                    onclick={onExportDocs}
                >
                    <MaterialDesignIcon iconName="download" class="w-4 h-4" />
                </button>
            {/if}
            <label
                class="p-1.5 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors cursor-pointer {status.status ===
                'extracting'
                    ? 'opacity-50 pointer-events-none'
                    : ''}"
                title={t("docs.btn_upload")}
            >
                <MaterialDesignIcon
                    iconName={status.status === "extracting" ? "loading" : "upload"}
                    class="w-4 h-4 {status.status === 'extracting' ? 'animate-spin' : ''}"
                />
                <input
                    type="file"
                    accept=".zip"
                    class="hidden"
                    disabled={status.status === "extracting"}
                    onchange={onZipUpload}
                />
            </label>
        </div>
    </div>

    <div class="flex bg-sem-surface-muted p-0.5 rounded-lg w-full">
        <button
            type="button"
            class="flex-1 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all flex items-center justify-center gap-1.5 {activeTab ===
            'meshchatx'
                ? 'bg-white dark:bg-zinc-700 text-sem-accent shadow-xs'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'}"
            onclick={() => onTabChange("meshchatx")}
        >
            <img src={MESHCHATX_LOGO_URL} alt="" class="w-3.5 h-3.5 object-contain shrink-0" />
            {t("docs.tab_meshchatx")}
        </button>
        <button
            type="button"
            class="flex-1 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all flex items-center justify-center gap-1.5 {activeTab ===
            'reticulum'
                ? 'bg-white dark:bg-zinc-700 text-sem-accent shadow-xs'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300'}"
            onclick={() => onTabChange("reticulum")}
        >
            <img src={RETICULUM_LOGO_URL} alt="" class="w-3.5 h-3.5 object-contain shrink-0" />
            {t("docs.tab_reticulum")}
        </button>
    </div>

    {#if status.has_docs || status.has_meshchatx_docs}
        <div class="relative w-full">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MaterialDesignIcon iconName="magnify" class="h-3.5 w-3.5 text-gray-400" />
            </div>
            <input
                type="text"
                bind:value={searchQuery}
                class="block w-full pl-9 pr-9 py-2 border border-sem-border rounded-lg bg-gray-50 dark:bg-zinc-800 text-sem-fg text-xs focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                placeholder={t("docs.search_placeholder_mobile")}
                oninput={(e) => onSearchInput((e.target as HTMLInputElement).value)}
            />
            {#if isSearching}
                <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <MaterialDesignIcon iconName="loading" class="h-3 w-3 text-gray-400 animate-spin" />
                </div>
            {:else if searchQuery}
                <button type="button" class="absolute inset-y-0 right-0 pr-3 flex items-center" onclick={onClearSearch}>
                    <MaterialDesignIcon
                        iconName="close"
                        class="h-3 w-3 text-gray-400 hover:text-gray-600 hover:text-sem-fg cursor-pointer"
                    />
                </button>
            {/if}
        </div>
    {/if}

    {#if activeTab === "meshchatx" && !searchQuery && visibleDocSections.length}
        <div class="space-y-2">
            <label class="text-[10px] font-bold uppercase tracking-widest text-sem-fg-muted" for="docs-mobile-select">
                {t("docs.sections_title")}
            </label>
            <select
                id="docs-mobile-select"
                value={selectedDocPath || ""}
                class="w-full bg-sem-surface-muted border border-sem-border rounded-xl text-xs font-medium p-2.5 text-sem-fg"
                onchange={(e) => onSelectDoc((e.target as HTMLSelectElement).value)}
            >
                {#each visibleDocSections as section (section.id)}
                    <optgroup label={section.title}>
                        {#each section.items as item (item.path)}
                            <option value={item.path}>
                                {item.title}
                            </option>
                        {/each}
                    </optgroup>
                {/each}
            </select>
        </div>
    {/if}
</div>
