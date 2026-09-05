<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { MESHCHATX_LOGO_URL, RETICULUM_LOGO_URL } from "../lib/constants.js";
    import type { DocLanguage, DocSection, DocsActiveTab, DocsStatus } from "../lib/types.js";
    import DocsSidebarSectionList from "./DocsSidebarSectionList.svelte";

    interface Props {
        activeTab: DocsActiveTab;
        status: DocsStatus;
        searchQuery: string;
        isSearching: boolean;
        currentLang: string;
        allLanguages: Array<{ code: string; name: string }>;
        meshchatxDocsLang: string;
        docLanguages: DocLanguage[];
        visibleDocSections: DocSection[];
        selectedDocPath: string | null;
        manifestWarning: string | null;
        meshchatxListError: string | null;
        localDocsUrl: string;
        onTabChange: (tab: DocsActiveTab) => void;
        onSearchInput: (value: string) => void;
        onClearSearch: () => void;
        onSwitchVersion: (version: string) => void;
        onDeleteVersion: (version: string) => void;
        onSetLanguage: (lang: string) => void;
        onSetMeshchatxDocsLang: (lang: string) => void;
        onSelectDoc: (path: string) => void;
        onExportDocs: () => void;
        onExportReticulumDocs: () => void;
        onZipUpload: (event: Event) => void;
    }

    let {
        activeTab,
        status,
        searchQuery = $bindable(),
        isSearching,
        currentLang,
        allLanguages,
        meshchatxDocsLang,
        docLanguages,
        visibleDocSections,
        selectedDocPath,
        manifestWarning,
        meshchatxListError,
        localDocsUrl,
        onTabChange,
        onSearchInput,
        onClearSearch,
        onSwitchVersion,
        onDeleteVersion,
        onSetLanguage,
        onSetMeshchatxDocsLang,
        onSelectDoc,
        onExportDocs,
        onExportReticulumDocs,
        onZipUpload,
    }: Props = $props();

    let showVersions = $state(false);
    let showLanguages = $state(false);
    let versionsDropdownEl = $state<HTMLElement | null>(null);
    let languagesDropdownEl = $state<HTMLElement | null>(null);

    onMount(() => {
        function handleClickOutside(event: MouseEvent): void {
            const target = event.target as Node | null;
            if (showVersions && versionsDropdownEl && !versionsDropdownEl.contains(target)) {
                showVersions = false;
            }
            if (showLanguages && languagesDropdownEl && !languagesDropdownEl.contains(target)) {
                showLanguages = false;
            }
        }
        document.addEventListener("click", handleClickOutside);
        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });
</script>

<!-- Desktop sidebar -->
<aside
    class="hidden lg:flex flex-col w-72 shrink-0 border-r border-sem-border bg-sem-canvas/80 dark:bg-zinc-950/80 z-30"
>
    <div class="p-3 border-b border-sem-border space-y-3 shrink-0">
        <a
            href="#/tools"
            class="inline-flex items-center gap-0.5 rounded-lg -ml-1 pl-0 pr-1.5 py-1.5 text-sm font-medium text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
            aria-label={t("tools.back_to_tools")}
        >
            <MaterialDesignIcon iconName="chevron-left" class="size-5 shrink-0" />
            <span class="truncate max-w-[8rem]">{t("app.tools")}</span>
        </a>

        <div class="flex bg-sem-surface-muted p-0.5 rounded-lg w-full">
            <button
                type="button"
                class="flex-1 px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all flex items-center justify-center gap-1.5 {activeTab ===
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
                class="flex-1 px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all flex items-center justify-center gap-1.5 {activeTab ===
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
                <div class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
                    <MaterialDesignIcon iconName="magnify" class="h-3.5 w-3.5 text-gray-400" />
                </div>
                <input
                    type="text"
                    bind:value={searchQuery}
                    class="block w-full pl-8 pr-8 py-1.5 border border-sem-border rounded-lg bg-gray-50 dark:bg-zinc-800 text-sem-fg text-[11px] focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                    placeholder={t("docs.search_placeholder")}
                    oninput={(e) => onSearchInput((e.target as HTMLInputElement).value)}
                />
                {#if isSearching}
                    <div class="absolute inset-y-0 right-0 pr-2.5 flex items-center">
                        <MaterialDesignIcon iconName="loading" class="h-3 w-3 text-gray-400 animate-spin" />
                    </div>
                {:else if searchQuery}
                    <button
                        type="button"
                        class="absolute inset-y-0 right-0 pr-2.5 flex items-center"
                        onclick={onClearSearch}
                    >
                        <MaterialDesignIcon
                            iconName="close"
                            class="h-3 w-3 text-gray-400 hover:text-gray-600 hover:text-sem-fg cursor-pointer"
                        />
                    </button>
                {/if}
            </div>
        {/if}

        <div class="flex items-center flex-wrap gap-1">
            {#if activeTab === "reticulum" && (status.has_docs || status.versions.length > 0)}
                <div class="relative" bind:this={versionsDropdownEl}>
                    <button
                        type="button"
                        class="p-1.5 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors flex items-center gap-1.5 {showVersions
                            ? 'bg-sem-surface-muted'
                            : ''}"
                        onclick={() => (showVersions = !showVersions)}
                    >
                        <MaterialDesignIcon iconName="history" class="w-4 h-4" />
                        <span class="text-[10px] font-bold uppercase truncate max-w-[5rem]">
                            {status.current_version || t("docs.default_version")}
                        </span>
                    </button>
                    {#if showVersions}
                        <div
                            class="absolute left-0 mt-2 w-48 bg-white dark:bg-zinc-800 border border-sem-border rounded-xl shadow-xl z-50 overflow-hidden"
                        >
                            <div
                                class="p-2 border-b border-gray-100 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-800/50"
                            >
                                <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                                    {t("docs.versions")}
                                </span>
                            </div>
                            <div class="max-h-64 overflow-y-auto py-1">
                                {#each status.versions as version (version)}
                                    <div
                                        class="w-full px-4 py-2 text-left text-[11px] hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors flex items-center justify-between group cursor-pointer {status.current_version ===
                                        version
                                            ? 'text-sem-accent font-bold'
                                            : 'text-sem-fg-muted'}"
                                        role="button"
                                        tabindex="0"
                                        onkeydown={(e) => {
                                            if (e.key === "Enter" || e.key === " ") {
                                                onSwitchVersion(version);
                                                showVersions = false;
                                            }
                                        }}
                                        onclick={() => {
                                            onSwitchVersion(version);
                                            showVersions = false;
                                        }}
                                    >
                                        <span class="truncate">{version}</span>
                                        <div class="flex items-center space-x-1">
                                            {#if status.current_version === version}
                                                <MaterialDesignIcon iconName="check" class="w-3.5 h-3.5" />
                                            {/if}
                                            {#if status.versions.length > 1}
                                                <button
                                                    type="button"
                                                    class="p-1 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    title="Delete this version"
                                                    onclick={(e) => {
                                                        e.stopPropagation();
                                                        onDeleteVersion(version);
                                                    }}
                                                >
                                                    <MaterialDesignIcon iconName="delete" class="w-3.5 h-3.5" />
                                                </button>
                                            {/if}
                                        </div>
                                    </div>
                                {/each}
                                {#if status.versions.length === 0}
                                    <div class="px-4 py-3 text-center text-gray-500 text-[10px]">
                                        {t("docs.no_versions")}
                                    </div>
                                {/if}
                            </div>
                            <div
                                class="p-2 border-t border-gray-100 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-800/50"
                            >
                                <label
                                    class="flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors text-[10px] font-bold uppercase"
                                >
                                    <MaterialDesignIcon iconName="upload" class="w-3.5 h-3.5" />
                                    <span>{t("docs.upload_zip")}</span>
                                    <input type="file" accept=".zip" class="hidden" onchange={onZipUpload} />
                                </label>
                            </div>
                        </div>
                    {/if}
                </div>
            {/if}

            {#if activeTab === "reticulum" && status.has_docs}
                <div class="relative" bind:this={languagesDropdownEl}>
                    <button
                        type="button"
                        class="p-1.5 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors flex items-center gap-1.5 {showLanguages
                            ? 'bg-sem-surface-muted'
                            : ''}"
                        onclick={() => (showLanguages = !showLanguages)}
                    >
                        <MaterialDesignIcon iconName="translate" class="w-4 h-4" />
                        <span class="text-[10px] font-bold uppercase">{currentLang}</span>
                    </button>
                    {#if showLanguages}
                        <div
                            class="absolute left-0 top-full mt-1 bg-sem-surface border border-sem-border rounded-lg shadow-xl p-1 min-w-[120px] z-20"
                        >
                            {#each allLanguages as lang (lang.code)}
                                <button
                                    type="button"
                                    class="flex items-center w-full px-3 py-2 text-[10px] font-bold uppercase hover:bg-sem-surface-muted rounded-md transition-colors {lang.code ===
                                    currentLang
                                        ? 'text-blue-500'
                                        : 'text-sem-fg-muted'}"
                                    onclick={() => {
                                        showLanguages = false;
                                        onSetLanguage(lang.code);
                                    }}
                                >
                                    {lang.name} ({lang.code})
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
            {/if}

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

            {#if status.has_docs}
                <button
                    type="button"
                    class="p-1.5 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors"
                    title={t("docs.btn_share")}
                    onclick={onExportReticulumDocs}
                >
                    <MaterialDesignIcon iconName="share-variant" class="w-4 h-4" />
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

            {#if status.has_docs}
                <a
                    href={localDocsUrl}
                    target="_blank"
                    rel="noreferrer"
                    class="inline-flex items-center px-2 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg hover:opacity-90 transition-opacity font-bold text-[10px] shadow-xs"
                >
                    <MaterialDesignIcon iconName="open-in-new" class="w-3 h-3 mr-1" />
                    {t("docs.open_external")}
                </a>
            {/if}
        </div>

        {#if activeTab === "meshchatx" && !searchQuery}
            <h3 class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
                {t("docs.sections_title")}
            </h3>
            {#if manifestWarning}
                <p
                    class="text-[11px] leading-relaxed text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/40 rounded-lg px-2.5 py-2"
                >
                    {manifestWarning}
                </p>
            {/if}
            {#if meshchatxListError}
                <p
                    class="text-[11px] leading-relaxed text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/40 rounded-lg px-2.5 py-2"
                >
                    {meshchatxListError}
                </p>
            {/if}
            {#if docLanguages.length > 1}
                <div class="flex flex-wrap gap-1.5">
                    {#each docLanguages as lang (lang.code)}
                        <button
                            type="button"
                            class="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide transition-colors {meshchatxDocsLang ===
                            lang.code
                                ? 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300'
                                : 'bg-sem-surface-muted text-sem-fg-muted hover:text-sem-fg'}"
                            onclick={() => onSetMeshchatxDocsLang(lang.code)}
                        >
                            {lang.code}
                        </button>
                    {/each}
                </div>
            {/if}
        {/if}
    </div>

    {#if activeTab === "meshchatx" && !searchQuery}
        <DocsSidebarSectionList {visibleDocSections} {selectedDocPath} {onSelectDoc} />
    {/if}
</aside>
