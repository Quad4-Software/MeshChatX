<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";
    import { filterLicenseRows } from "./lib/licenseFilter.js";

    let loading = $state(true);
    let loadError = $state(/** @type {string | null} */ (null));
    let searchQuery = $state("");
    /** @type {Array<{ name: string, version: string, author: string, license: string }>} */
    let backend = $state([]);
    /** @type {typeof backend} */
    let frontend = $state([]);
    /** @type {{ generated_at?: string, frontend_source?: string } | null} */
    let meta = $state(null);

    const filteredBackend = $derived(filterLicenseRows(backend, searchQuery));
    const filteredFrontend = $derived(filterLicenseRows(frontend, searchQuery));

    async function load() {
        loading = true;
        loadError = null;
        try {
            const res = await window.api.get("/api/v1/licenses");
            backend = res.data.backend || [];
            frontend = res.data.frontend || [];
            meta = res.data.meta || null;
        } catch (e) {
            loadError = e.response?.data?.error || e.message || "Failed to load licenses";
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        load();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-surface" data-testid="licenses-page">
    <div class="flex-1 flex flex-col min-h-0 overflow-y-auto overscroll-y-contain w-full">
        <div class="shrink-0 border-b border-sem-border px-3 sm:px-4 md:px-6 py-4 md:py-5">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
                <div class="space-y-2 min-w-0 flex-1">
                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                        {t("licenses.section_label")}
                    </div>
                    <div class="text-xl sm:text-2xl md:text-3xl font-black text-sem-fg tracking-tight">
                        {t("licenses.title")}
                    </div>
                    <div class="text-sm text-sem-fg-muted leading-relaxed max-w-2xl">
                        {t("licenses.description")}
                    </div>
                    {#if meta?.generated_at}
                        <p class="text-xs text-sem-fg-muted wrap-break-word">
                            {t("licenses.generated_at", { time: meta.generated_at })}
                            {#if meta.frontend_source}
                                <span class="ml-2 inline-block sm:inline">
                                    ({t("licenses.frontend_source", { source: meta.frontend_source })})
                                </span>
                            {/if}
                        </p>
                    {/if}
                </div>

                <div class="w-full lg:max-w-md xl:max-w-sm shrink-0">
                    <div class="relative group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                            <MaterialDesignIcon iconName="magnify" />
                        </div>
                        <input
                            bind:value={searchQuery}
                            type="search"
                            enterkeyhint="search"
                            autocomplete="off"
                            placeholder={t("licenses.search_placeholder")}
                            class="w-full min-h-[44px] sm:min-h-0 pl-10 pr-10 py-3 bg-sem-surface-muted border border-sem-border rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sem-focus/40 focus:border-sem-focus-border text-sem-fg placeholder:text-sem-fg-muted text-base sm:text-sm"
                        />
                        {#if searchQuery}
                            <button
                                class="absolute inset-y-0 right-0 pr-3 flex items-center min-w-[44px] justify-end text-sem-fg-muted hover:text-sem-fg"
                                type="button"
                                aria-label="Clear search"
                                onclick={() => (searchQuery = "")}
                            >
                                <MaterialDesignIcon iconName="close-circle" />
                            </button>
                        {/if}
                    </div>
                </div>
            </div>
        </div>

        <div
            class="flex-1 min-h-0 p-3 sm:p-4 md:p-6 xl:p-8 w-full max-w-6xl xl:max-w-[min(100%,96rem)] mx-auto flex flex-col gap-4"
        >
            {#if loadError}
                <div
                    class="rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-800 dark:text-red-200"
                >
                    {loadError}
                </div>
            {/if}

            {#if loading}
                <div class="flex flex-col items-center justify-center py-16 gap-3 text-sem-fg-muted">
                    <span class="animate-spin inline-flex"><MaterialDesignIcon iconName="loading" /></span>
                    <span>{t("common.loading")}</span>
                </div>
            {:else}
                <div class="license-grid grid grid-cols-1 gap-4 xl:grid-cols-2 xl:gap-6 xl:items-start">
                    {#each [{ key: "backend", rows: filteredBackend, titleKey: "licenses.backend_section" }, { key: "frontend", rows: filteredFrontend, titleKey: "licenses.frontend_section" }] as section (section.key)}
                        <details
                            class="license-details rounded-lg border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 open:bg-white dark:open:bg-zinc-950 overflow-hidden"
                            open
                        >
                            <summary
                                class="cursor-pointer select-none px-3 sm:px-4 py-3.5 sm:py-3 min-h-[48px] sm:min-h-0 font-semibold text-sm sm:text-base text-sem-fg flex items-center justify-between gap-2 list-none touch-manipulation"
                            >
                                <span class="min-w-0 wrap-break-word pr-2"
                                    >{t(section.titleKey)} ({section.rows.length})</span
                                >
                                <span class="license-details-chevron opacity-60 shrink-0">
                                    <MaterialDesignIcon iconName="chevron-down" />
                                </span>
                            </summary>
                            <div
                                class="license-details-body border-t border-gray-100/80 dark:border-zinc-800/50 max-h-[min(65vh,32rem)] xl:max-h-[min(calc(100dvh-14rem),44rem)] overflow-x-auto overflow-y-auto overscroll-contain px-1 sm:px-2 pb-3 sm:pb-4"
                            >
                                <table class="min-w-full text-left border-collapse text-xs sm:text-sm">
                                    <thead>
                                        <tr
                                            class="sticky top-0 z-1 border-b border-sem-border bg-gray-50/95 dark:bg-zinc-900/95 backdrop-blur-xs text-sem-fg-muted"
                                        >
                                            <th class="py-2 px-2 sm:px-3 font-medium">{t("licenses.col_package")}</th>
                                            <th class="py-2 px-2 sm:px-3 font-medium whitespace-nowrap"
                                                >{t("licenses.col_version")}</th
                                            >
                                            <th class="py-2 px-2 sm:px-3 font-medium">{t("licenses.col_author")}</th>
                                            <th class="py-2 px-2 sm:px-3 font-medium">{t("licenses.col_license")}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#each section.rows as row (`${section.key}-${row.name}-${row.version}`)}
                                            <tr
                                                class="border-b border-sem-border/80 hover:bg-gray-50/80 dark:hover:bg-zinc-900/60"
                                            >
                                                <td
                                                    class="py-2 px-2 sm:px-3 font-mono text-[11px] sm:text-xs text-sem-fg align-top"
                                                    >{row.name}</td
                                                >
                                                <td
                                                    class="py-2 px-2 sm:px-3 text-sem-fg-muted align-top whitespace-nowrap"
                                                    >{row.version}</td
                                                >
                                                <td
                                                    class="py-2 px-2 sm:px-3 text-sem-fg-muted max-w-40 sm:max-w-56 truncate align-top"
                                                    title={row.author}>{row.author}</td
                                                >
                                                <td
                                                    class="py-2 px-2 sm:px-3 text-sem-fg-muted max-w-32 sm:max-w-xs align-top wrap-break-word"
                                                    >{row.license}</td
                                                >
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                                {#if section.rows.length === 0}
                                    <p class="text-center py-8 text-sem-fg-muted text-sm">{t("common.no_results")}</p>
                                {/if}
                            </div>
                        </details>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
</div>

<style>
    .license-details summary::-webkit-details-marker {
        display: none;
    }
    .license-details summary::marker {
        display: none;
    }
    .license-details[open] .license-details-chevron {
        transform: rotate(180deg);
    }
    .license-details-chevron {
        display: inline-flex;
        transition: transform 0.15s ease;
    }
    .license-details-body {
        -webkit-overflow-scrolling: touch;
    }
</style>
