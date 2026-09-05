<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import { SvelteMap } from "svelte/reactivity";
    import DialogUtils from "../../js/DialogUtils.js";
    import GlobalState from "../../js/GlobalState.js";
    import {
        invalidateNomadMicronWasmPreload,
        isMicronWasmBundled,
        preloadNomadMicronWasm,
    } from "../../js/MicronWasmLoader.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ArchiveCard from "./components/ArchiveCard.svelte";
    import ArchiveViewer from "./components/ArchiveViewer.svelte";
    import { exportArchiveAsMu } from "./lib/archiveExport.js";
    import {
        handleArchiveContentClick,
        openInNomadnet,
        type RouterLike,
    } from "./lib/archiveNavigation.js";
    import { renderFullContent, shortHash } from "./lib/archiveRender.js";
    import {
        API_NOMADNET_ARCHIVES,
        API_NOMADNET_ARCHIVES_RECRAWL,
        API_NOMADNET_OPT_OUTS,
        DEFAULT_PAGE_LIMIT,
        SEARCH_DEBOUNCE_MS,
        SPLIT_MIN_WIDTH,
    } from "./lib/constants.js";
    import type {
        ArchiveItem,
        ArchiveItemApiResponse,
        ArchivePagination,
        ArchiveRecrawlApiResponse,
        ArchivesApiResponse,
        NodeOption,
        NomadRenderOptions,
    } from "./lib/types.js";

    interface Props {
        routeQuery?: Record<string, string>;
        router?: RouterLike;
    }

    let { routeQuery = {}, router }: Props = $props();

    let archives = $state<ArchiveItem[]>([]);
    let isLoading = $state(false);
    let isSearching = $state(false);
    let isLoadingViewer = $state(false);
    let isRecrawling = $state(false);
    let loadError = $state(false);
    let viewingArchive = $state<ArchiveItem | null>(null);
    let renderedContent = $state("");
    let searchQuery = $state("");
    let nodeFilter = $state("");
    let nodeOptions = $state<NodeOption[]>([]);
    let isWideSplit = $state(false);
    let cardPreviewCache = $state<Record<string, string>>({});
    let nomadMicronWasmReady = $state(false);
    let searchTimeout: ReturnType<typeof setTimeout> | null = null;

    let pagination = $state<ArchivePagination>({
        page: 1,
        limit: DEFAULT_PAGE_LIMIT,
        total_count: 0,
        total_pages: 0,
    });

    const rangeStart = $derived(
        pagination.total_count > 0 ? (pagination.page - 1) * pagination.limit + 1 : 0
    );

    const rangeEnd = $derived(
        Math.min(pagination.page * pagination.limit, pagination.total_count)
    );

    const nomadMicronWasmFeatureEffective: boolean = $derived(
        Boolean(isMicronWasmBundled()) && (GlobalState.config || {}).nomad_micron_wasm_enabled === true
    );

    const nomadMicronWasmActive: boolean = $derived(
        Boolean(
            nomadMicronWasmFeatureEffective &&
            nomadMicronWasmReady &&
            typeof globalThis.micronConvert === "function" &&
            ((GlobalState.config?.nomad_micron_default_engine || "js") === "wasm")
        )
    );

    const nomadRenderOptions = $derived<NomadRenderOptions>({
        renderMarkdown: GlobalState.config?.nomad_render_markdown_enabled !== false,
        renderHtml: GlobalState.config?.nomad_render_html_enabled !== false,
        renderPlaintext: GlobalState.config?.nomad_render_plaintext_enabled !== false,
        nomadDestinationHash: viewingArchive?.destination_hash || null,
        nomad_micron_wasm_use:
            Boolean(nomadMicronWasmFeatureEffective) &&
            Boolean(nomadMicronWasmReady) &&
            ((GlobalState.config?.nomad_micron_default_engine || "js") === "wasm"),
    });

    function updateWideSplit(): void {
        isWideSplit = typeof window !== "undefined" && window.innerWidth >= SPLIT_MIN_WIDTH;
    }

    function refreshNodeOptions(): void {
        const map = new SvelteMap<string, NodeOption>();
        for (const a of archives) {
            if (!map.has(a.destination_hash)) {
                map.set(a.destination_hash, {
                    hash: a.destination_hash,
                    label: `${a.node_name} (${shortHash(a.destination_hash)})`,
                });
            }
        }
        if (nodeFilter && !map.has(nodeFilter)) {
            map.set(nodeFilter, {
                hash: nodeFilter,
                label: shortHash(nodeFilter),
            });
        }
        nodeOptions = Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label));
    }

    async function getArchives(): Promise<void> {
        isLoading = true;
        isSearching = Boolean(searchQuery);
        loadError = false;
        try {
            const params: Record<string, unknown> = {
                page: pagination.page,
                limit: pagination.limit,
                include_content: false,
            };
            if (searchQuery) {
                params.q = searchQuery;
            }
            if (nodeFilter) {
                params.destination_hash = nodeFilter;
            }
            const response = await window.api.get(API_NOMADNET_ARCHIVES, { params });
            const data = response.data as ArchivesApiResponse | undefined;
            archives = data?.archives || [];
            const pag = data?.pagination || {};
            pagination = {
                page: pag.page || pagination.page,
                limit: pag.limit || pagination.limit,
                total_count: pag.total_count || 0,
                total_pages: pag.total_pages || 0,
            };
            refreshNodeOptions();
            cardPreviewCache = {};
        } catch (e) {
            console.error("Failed to load archives:", e);
            loadError = true;
            ToastUtils.error(t("archives.search_failed"));
        } finally {
            isLoading = false;
            isSearching = false;
        }
    }

    function onSearchInput(): void {
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        isSearching = true;
        searchTimeout = setTimeout(() => {
            pagination.page = 1;
            getArchives();
        }, SEARCH_DEBOUNCE_MS);
    }

    function clearSearch(): void {
        searchQuery = "";
        pagination.page = 1;
        getArchives();
    }

    function onFilterChange(): void {
        pagination.page = 1;
        getArchives();
    }

    function goPage(page: number): void {
        pagination.page = page;
        getArchives();
    }

    async function openArchive(archive: ArchiveItem): Promise<void> {
        isLoadingViewer = true;
        viewingArchive = { ...archive, content: archive.content || null };
        try {
            const response = await window.api.get(`${API_NOMADNET_ARCHIVES}/${archive.id}`);
            const full = (response.data as ArchiveItemApiResponse | undefined)?.archive;
            if (full) {
                viewingArchive = full;
                renderedContent = renderFullContent(full, nomadRenderOptions, nomadMicronWasmActive);
            }
        } catch (e) {
            console.error("Failed to load archive:", e);
            ToastUtils.error(t("archives.failed_load"));
            viewingArchive = null;
        } finally {
            isLoadingViewer = false;
        }
    }

    function closeViewer(): void {
        viewingArchive = null;
        renderedContent = "";
    }

    async function recrawlArchive(archive: ArchiveItem): Promise<void> {
        if (!archive || isRecrawling) {
            return;
        }
        isRecrawling = true;
        const toastKey = `archives-recrawl-${archive.id || archive.destination_hash}`;
        ToastUtils.loading(t("archives.recrawl_pending"), 0, toastKey);
        try {
            const response = await window.api.post(API_NOMADNET_ARCHIVES_RECRAWL, {
                destination_hash: archive.destination_hash,
                page_path: archive.page_path,
            });
            ToastUtils.dismiss(toastKey);
            const next = (response.data as ArchiveRecrawlApiResponse | undefined)?.archive;
            ToastUtils.success(t("archives.recrawl_done"));
            if (next) {
                viewingArchive = next;
                renderedContent = renderFullContent(next, nomadRenderOptions, nomadMicronWasmActive);
                const idx = archives.findIndex(
                    (a) => a.destination_hash === next.destination_hash && a.page_path === next.page_path
                );
                if (idx >= 0) {
                    archives[idx] = {
                        ...archives[idx],
                        ...next,
                        content: undefined,
                    };
                } else {
                    archives.unshift({
                        ...next,
                        content: undefined,
                    });
                }
                cardPreviewCache = {};
            } else {
                await getArchives();
            }
        } catch (e: any) {
            ToastUtils.dismiss(toastKey);
            console.error("Recrawl failed:", e);
            const msg = e?.response?.data?.message || t("archives.recrawl_failed");
            ToastUtils.error(msg);
        } finally {
            isRecrawling = false;
        }
    }

    async function deleteArchive(archive: ArchiveItem): Promise<void> {
        if (!(await DialogUtils.confirm(t("archives.delete_snapshot_confirm")))) {
            return;
        }
        try {
            await window.api.delete(API_NOMADNET_ARCHIVES, {
                data: { ids: [archive.id] },
            });
            archives = archives.filter((a) => a.id !== archive.id);
            if (viewingArchive?.id === archive.id) {
                closeViewer();
            }
            pagination.total_count = Math.max(0, pagination.total_count - 1);
            ToastUtils.success(t("archives.deleted"));
        } catch (e) {
            console.error("Failed to delete archive:", e);
            ToastUtils.error(t("archives.failed_delete"));
        }
    }

    async function optOutNode(archive: ArchiveItem): Promise<void> {
        if (!(await DialogUtils.confirm(t("archives.never_crawl_confirm")))) {
            return;
        }
        try {
            await window.api.post(API_NOMADNET_OPT_OUTS, {
                destination_hash: archive.destination_hash,
                reason: "user",
            });
            ToastUtils.success(t("archives.never_crawl_saved"));
        } catch (e) {
            console.error("Failed to opt out node:", e);
            ToastUtils.error(t("archives.never_crawl_failed"));
        }
    }

    function handleOpenInNomadnet(archive: ArchiveItem): void {
        openInNomadnet(archive, router);
    }

    function handleContentClick(event: MouseEvent): void {
        handleArchiveContentClick(event, router);
    }

    onMount(() => {
        updateWideSplit();
        window.addEventListener("resize", updateWideSplit);
        const q = routeQuery?.q;
        if (typeof q === "string" && q) {
            searchQuery = q;
        }
        getArchives();

        const cfg = (GlobalState.config || {}) as Record<string, unknown>;
        if (isMicronWasmBundled() && cfg.nomad_micron_wasm_enabled === true) {
            preloadNomadMicronWasm().then((ok) => {
                nomadMicronWasmReady = ok === true;
                cardPreviewCache = {};
                if (viewingArchive && ok) {
                    renderedContent = renderFullContent(
                        viewingArchive,
                        nomadRenderOptions,
                        nomadMicronWasmActive
                    );
                }
            });
        }

        return () => {
            window.removeEventListener("resize", updateWideSplit);
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
        };
    });
</script>

<div class="flex h-full min-h-0 flex-col overflow-hidden bg-sem-canvas text-sem-fg" data-testid="archives-page">
    <div class="shrink-0 border-b border-sem-border px-3 py-3 sm:px-4">
        <div class="mx-auto flex w-full max-w-6xl flex-col gap-3">
            <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                    <h1 class="text-lg font-semibold sm:text-xl">{t("archives.title")}</h1>
                    <p class="mt-0.5 text-xs text-sem-fg-muted sm:text-sm">{t("archives.description")}</p>
                </div>
                {#if viewingArchive && !isWideSplit}
                    <button
                        type="button"
                        class="rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60"
                        title={t("archives.close_viewer")}
                        onclick={closeViewer}
                    >
                        <MaterialDesignIcon iconName="close" class="size-5" />
                    </button>
                {/if}
            </div>

            {#if !viewingArchive || isWideSplit}
                <div class="relative">
                    <MaterialDesignIcon
                        iconName="magnify"
                        class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-sem-fg-muted"
                    />
                    <input
                        bind:value={searchQuery}
                        type="search"
                        placeholder={t("archives.search_placeholder")}
                        class="w-full rounded-xl border border-sem-border bg-sem-surface py-2.5 pl-10 pr-10 text-sm text-sem-fg placeholder:text-sem-fg-muted focus:border-sem-accent focus:outline-hidden focus:ring-2 focus:ring-sem-accent/20"
                        oninput={onSearchInput}
                    />
                    {#if isSearching}
                        <div class="absolute inset-y-0 right-3 flex items-center">
                            <MaterialDesignIcon iconName="loading" class="size-4 animate-spin text-sem-fg-muted" />
                        </div>
                    {:else if searchQuery}
                        <button
                            type="button"
                            class="absolute inset-y-0 right-2 flex items-center rounded p-1 text-sem-fg-muted hover:text-sem-fg"
                            title={t("archives.clear_search")}
                            onclick={clearSearch}
                        >
                            <MaterialDesignIcon iconName="close" class="size-4" />
                        </button>
                    {/if}
                </div>

                <div class="flex flex-wrap items-center gap-2 text-xs text-sem-fg-muted">
                    {#if pagination.total_count > 0}
                        <span class="rounded-full bg-sem-surface-muted px-2 py-0.5 font-medium">
                            {searchQuery
                                ? t("archives.matches_count", { count: pagination.total_count })
                                : t("archives.showing_range", {
                                      start: rangeStart,
                                      end: rangeEnd,
                                      total: pagination.total_count,
                                  })}
                        </span>
                    {/if}
                    <label class="ml-auto flex items-center gap-1.5">
                        <span>{t("archives.filter_node")}</span>
                        <select
                            bind:value={nodeFilter}
                            class="rounded-lg border border-sem-border bg-sem-canvas px-2 py-1 text-xs text-sem-fg"
                            onchange={onFilterChange}
                        >
                            <option value="">{t("archives.all_nodes")}</option>
                            {#each nodeOptions as node (node.hash)}
                                <option value={node.hash}>
                                    {node.label}
                                </option>
                            {/each}
                        </select>
                    </label>
                </div>
            {/if}
        </div>
    </div>

    <div
        class="mx-auto flex min-h-0 w-full max-w-6xl flex-1 overflow-hidden {isWideSplit
            ? 'flex-row'
            : 'flex-col'}"
    >
        {#if !viewingArchive || isWideSplit}
            <div
                class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden {isWideSplit && viewingArchive
                    ? 'lg:max-w-md lg:border-r lg:border-sem-border xl:max-w-lg'
                    : ''}"
            >
                {#if loadError}
                    <div class="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
                        <MaterialDesignIcon iconName="alert-circle-outline" class="size-10 text-red-400" />
                        <p class="text-sm">{t("archives.search_failed")}</p>
                        <button type="button" class="text-xs font-medium text-sem-accent" onclick={getArchives}>
                            {t("archives.retry")}
                        </button>
                    </div>
                {:else if !isLoading && archives.length === 0}
                    <div class="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
                        <MaterialDesignIcon iconName="text-search" class="size-12 text-sem-fg-muted opacity-40" />
                        <p class="text-sm font-medium">
                            {searchQuery ? t("archives.no_results") : t("archives.no_archives")}
                        </p>
                        <p class="max-w-sm text-xs text-sem-fg-muted">
                            {searchQuery ? t("archives.adjust_filters") : t("archives.browse_to_archive")}
                        </p>
                        {#if searchQuery}
                            <button
                                type="button"
                                class="mt-2 text-xs font-medium text-sem-accent"
                                onclick={clearSearch}
                            >
                                {t("archives.clear_search")}
                            </button>
                        {/if}
                    </div>
                {:else}
                    <div class="flex-1 overflow-y-auto">
                        <div class="grid grid-cols-1 gap-3 p-3 sm:p-4 {!viewingArchive ? 'sm:grid-cols-2' : ''}">
                            {#each archives as archive (archive.id)}
                                <ArchiveCard
                                    {archive}
                                    isSelected={viewingArchive?.id === archive.id}
                                    {searchQuery}
                                    {cardPreviewCache}
                                    {nomadMicronWasmActive}
                                    {nomadRenderOptions}
                                    onSelect={openArchive}
                                />
                            {/each}
                        </div>

                        {#if pagination.total_pages > 1}
                            <div class="flex items-center justify-center gap-3 border-t border-sem-border px-3 py-3">
                                <button
                                    type="button"
                                    class="rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40"
                                    disabled={pagination.page <= 1 || isLoading}
                                    onclick={() => goPage(pagination.page - 1)}
                                >
                                    {t("archives.prev_page")}
                                </button>
                                <span class="text-xs text-sem-fg-muted">
                                    {t("archives.page_of", {
                                        page: pagination.page,
                                        total_pages: pagination.total_pages,
                                    })}
                                </span>
                                <button
                                    type="button"
                                    class="rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40"
                                    disabled={pagination.page >= pagination.total_pages || isLoading}
                                    onclick={() => goPage(pagination.page + 1)}
                                >
                                    {t("archives.next_page")}
                                </button>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}

        {#if viewingArchive}
            <ArchiveViewer
                {viewingArchive}
                {renderedContent}
                {isLoadingViewer}
                {isRecrawling}
                {isWideSplit}
                onClose={closeViewer}
                onRecrawl={recrawlArchive}
                onExport={exportArchiveAsMu}
                onOpenLive={handleOpenInNomadnet}
                onOptOut={optOutNode}
                onDelete={deleteArchive}
                onContentClick={handleContentClick}
            />
        {/if}
    </div>
</div>
