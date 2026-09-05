<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import EmptyState from "../../ui/svelte/EmptyState.svelte";
    import { t } from "../../js/i18n.js";
    import ToolListRow from "./ToolListRow.svelte";
    import ToolsSection from "./ToolsSection.svelte";
    import {
        filterTools,
        groupTools,
        loadCollapsedSections,
        saveCollapsedSections,
        toolRouteHref,
        toolRowClass,
        translateTools,
    } from "./lib/toolsList.js";

    let searchQuery = $state("");
    /** @type {Record<string, boolean>} */
    let collapsedSections = $state(loadCollapsedSections());

    const toolsWithTranslations = $derived(translateTools(t));
    const filteredTools = $derived(filterTools(toolsWithTranslations, searchQuery));
    const groupedToolSections = $derived(searchQuery.trim() ? null : groupTools(filteredTools));
    const toolsCount = $derived(toolsWithTranslations.length);

    /**
     * @param {string} sectionId
     */
    function toggleSection(sectionId) {
        const next = { ...collapsedSections, [sectionId]: !collapsedSections[sectionId] };
        collapsedSections = next;
        saveCollapsedSections(next);
    }
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="tools-page">
    <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div class="border-b border-sem-border px-4 py-2.5 md:px-6 md:py-3">
            <div class="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                <div class="min-w-0 flex-1">
                    <div class="text-xl md:text-2xl font-bold text-sem-fg tracking-tight">
                        {t("tools.power_tools")}
                    </div>
                    <div class="text-xs sm:text-sm text-sem-fg-muted leading-snug max-w-xl mt-0.5">
                        {t("tools.diagnostics_description")}
                    </div>
                </div>

                <div class="w-full sm:max-w-sm shrink-0">
                    <div class="relative group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MaterialDesignIcon
                                iconName="magnify"
                                class="size-5 text-gray-400 group-focus-within:text-sem-accent transition-colors"
                            />
                        </div>
                        <input
                            bind:value={searchQuery}
                            type="text"
                            placeholder={t("tools.search_placeholder", { count: toolsCount })}
                            class="input-field w-full pl-10! pr-10 py-2!"
                        />
                        {#if searchQuery}
                            <button
                                class="absolute inset-y-0 right-0 pr-3 flex items-center text-sem-fg-muted hover:text-sem-fg focus-ring-sem rounded-lg"
                                type="button"
                                aria-label="Clear search"
                                onclick={() => (searchQuery = "")}
                            >
                                <MaterialDesignIcon iconName="close-circle" class="size-5" />
                            </button>
                        {/if}
                    </div>
                </div>
            </div>
        </div>

        <div class="p-4 md:p-6 xl:p-8 w-full max-w-6xl xl:max-w-7xl 2xl:max-w-384 mx-auto">
            {#if groupedToolSections}
                {#each groupedToolSections as section (section.id)}
                    <ToolsSection
                        sectionId={section.id}
                        tools={section.tools}
                        collapsed={!!collapsedSections[section.id]}
                        onToggle={toggleSection}
                    />
                {/each}
            {:else if filteredTools.length > 0}
                <div class="rounded-lg overflow-hidden border border-sem-border bg-sem-surface">
                    <div
                        class="grid grid-cols-1 lg:grid-cols-2 divide-y divide-sem-border divide-x-0 lg:divide-x lg:divide-y"
                    >
                        {#each filteredTools as tool (String(tool.name))}
                            {#if tool.comingSoon}
                                <div class={toolRowClass(tool)}>
                                    <ToolListRow {tool} />
                                </div>
                            {:else}
                                <a
                                    href={toolRouteHref(
                                        /** @type {{ name?: string, path?: string } | string} */ (tool.route)
                                    )}
                                    class={toolRowClass(tool)}
                                >
                                    <ToolListRow {tool} />
                                </a>
                            {/if}
                        {/each}
                    </div>
                </div>
            {/if}

            {#if filteredTools.length === 0}
                <EmptyState class="mt-6" icon="magnify" title={t("common.no_results")} />
            {/if}
        </div>
    </div>
</div>

<style>
    :global(.tool-row) {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
        min-height: 4.25rem;
        transition: background-color 0.15s ease;
    }
    @media (min-width: 640px) {
        :global(.tool-row) {
            align-items: center;
            gap: 1rem;
        }
    }
    :global(.tool-row:hover) {
        background-color: color-mix(in oklab, var(--mc-surface-muted, #f4f4f5) 100%, transparent);
    }
</style>
