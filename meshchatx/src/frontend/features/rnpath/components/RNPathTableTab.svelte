<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import ManagementIdentityPicker from "./ManagementIdentityPicker.svelte";
    import { t } from "../../../js/i18n.js";
    import { getStateColor, getStateText, formatDate } from "../lib/pathQuery.js";
    import { ITEMS_PER_PAGE_OPTIONS } from "../lib/constants.js";
    import type { PathEntry } from "../lib/types.js";

    interface Props {
        pathTable?: PathEntry[];
        totalItems?: number;
        responsiveItems?: number;
        unresponsiveItems?: number;
        interfaces?: string[];
        remoteHash?: string;
        identityPath?: string;
        remoteTimeout?: number;
        activeRemoteHash?: string;
        searchQuery?: string;
        filterInterface?: string;
        filterHops?: number | string | null;
        currentPage?: number;
        itemsPerPage?: number;
        totalPages?: number;
        onDropPath?: (hash: string) => void;
        onClearRemote?: () => void;
        onFilterChange?: () => void;
        onPageChange?: (page: number) => void;
    }

    let {
        pathTable = [],
        totalItems = 0,
        responsiveItems = 0,
        unresponsiveItems = 0,
        interfaces = [],
        remoteHash = $bindable(""),
        identityPath = $bindable(""),
        remoteTimeout = $bindable(15),
        activeRemoteHash = "",
        searchQuery = $bindable(""),
        filterInterface = $bindable(""),
        filterHops = $bindable<number | string | null>(null),
        currentPage = $bindable(1),
        itemsPerPage = $bindable(50),
        totalPages = 1,
        onDropPath,
        onClearRemote,
        onFilterChange,
        onPageChange,
    }: Props = $props();

    function prevPage(): void {
        if (currentPage > 1) {
            currentPage -= 1;
            onPageChange?.(currentPage);
        }
    }

    function nextPage(): void {
        if (currentPage < totalPages) {
            currentPage += 1;
            onPageChange?.(currentPage);
        }
    }

    function handleSearchInput(e: Event): void {
        searchQuery = (e.target as HTMLInputElement).value;
        onFilterChange?.();
    }

    function handleInterfaceChange(e: Event): void {
        filterInterface = (e.target as HTMLSelectElement).value;
        onFilterChange?.();
    }

    function handleHopsInput(e: Event): void {
        const val = (e.target as HTMLInputElement).value;
        filterHops = val === "" ? null : Number(val);
        onFilterChange?.();
    }

    function handleItemsPerPageChange(e: Event): void {
        itemsPerPage = Number((e.target as HTMLSelectElement).value);
        onFilterChange?.();
    }
</script>

<div class="space-y-4">
    <div class="rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4 space-y-3">
        <div class="text-sm font-semibold">{t("rnstatus.remote_query")}</div>
        <p class="text-xs text-gray-500">{t("rnstatus.remote_query_hint")}</p>
        <div class="grid gap-3 lg:grid-cols-2">
            <input
                bind:value={remoteHash}
                type="text"
                class="input-field font-mono text-xs"
                placeholder={t("rnstatus.remote_transport_placeholder")}
            />
            <input
                bind:value={remoteTimeout}
                type="number"
                min="1"
                class="input-field text-sm"
                placeholder={t("rnstatus.remote_timeout")}
            />
        </div>
        <ManagementIdentityPicker bind:value={identityPath} defaultName="mgmt" />
        {#if activeRemoteHash}
            <div class="flex flex-wrap items-center gap-2 text-xs">
                <span class="font-mono text-amber-700 dark:text-amber-300">
                    {t("rnstatus.remote_active", { hash: activeRemoteHash })}
                </span>
                <button type="button" class="secondary-chip px-2 py-1 text-xs cursor-pointer" onclick={onClearRemote}>
                    {t("rnstatus.use_local")}
                </button>
            </div>
        {/if}
    </div>

    <!-- filters -->
    <div
        class="rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4"
    >
        <div class="relative">
            <input
                value={searchQuery}
                oninput={handleSearchInput}
                type="text"
                placeholder={t("tools.rnpath.search_placeholder")}
                class="input-field pr-10"
                autocomplete="off"
            />
            <MaterialDesignIcon
                iconName="magnify"
                class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
            />
        </div>
        <select value={filterInterface} onchange={handleInterfaceChange} class="input-field">
            <option value="">{t("tools.rnpath.all_interfaces")}</option>
            {#each interfaces as iface (iface)}
                <option value={iface}>
                    {iface}
                </option>
            {/each}
        </select>
        <div class="flex items-center gap-2">
            <span class="text-xs font-semibold text-sem-fg-muted uppercase min-w-fit">{t("rnprobe.hops")}:</span>
            <input
                value={filterHops ?? ""}
                oninput={handleHopsInput}
                type="number"
                min="0"
                max="128"
                placeholder={t("common.all")}
                class="input-field"
            />
        </div>
        <div
            class="flex flex-wrap items-center justify-start sm:justify-end gap-x-4 gap-y-2 sm:flex-nowrap lg:col-span-1"
        >
            <div class="flex flex-col items-start sm:items-end">
                <span class="text-[10px] font-bold text-gray-400 uppercase">{t("tools.rnpath.total")}</span>
                <span class="text-sm font-bold text-sem-fg">{totalItems}</span>
            </div>
            <div class="flex flex-col items-start sm:items-end">
                <span class="text-[10px] font-bold text-green-500 uppercase">{t("tools.rnpath.responsive")}</span>
                <span class="text-sm font-bold text-green-600 dark:text-green-400">{responsiveItems}</span>
            </div>
            <div class="flex flex-col items-start sm:items-end">
                <span class="text-[10px] font-bold text-red-500 uppercase">{t("tools.rnpath.unresponsive")}</span>
                <span class="text-sm font-bold text-red-600 dark:text-red-400">{unresponsiveItems}</span>
            </div>
        </div>
    </div>

    {#if pathTable.length === 0}
        <EmptyState
            icon="map-marker-path"
            title={t("tools.rnpath.no_paths_title")}
            description={t("tools.rnpath.no_paths_desc")}
        />
    {:else}
        <div class="grid gap-4">
            {#each pathTable as path (path.hash)}
                <div
                    class="rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-l-4 {path.state ===
                    2
                        ? 'border-l-green-500'
                        : path.state === 1
                          ? 'border-l-red-500'
                          : 'border-l-gray-300 dark:border-l-zinc-700'}"
                >
                    <div class="min-w-0">
                        <div class="flex flex-wrap items-center gap-2 mb-1">
                            <span class="font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400 truncate">
                                {path.hash}
                            </span>
                            <span
                                class="px-2 py-0.5 text-[10px] font-bold bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-sm uppercase tracking-wider"
                            >
                                {path.hops}
                                {path.hops === 1 ? "hop" : "hops"}
                            </span>
                            <span
                                class="px-2 py-0.5 text-[10px] font-bold rounded-sm uppercase tracking-wider {getStateColor(
                                    path.state
                                )}"
                            >
                                {getStateText(path.state)}
                            </span>
                        </div>
                        <div class="text-xs text-sem-fg-muted font-mono truncate">
                            via {path.via} on {path.interface}
                        </div>
                        <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[10px]">
                            <div class="text-sem-fg-muted">
                                <span class="font-semibold uppercase">{t("tools.rnpath.last_updated")}:</span>
                                {path.timestamp ? formatDate(path.timestamp) : "Unknown"}
                            </div>
                            <div class="text-sem-fg-muted">
                                <span class="font-semibold uppercase">{t("tools.rnpath.expires")}:</span>
                                {formatDate(path.expires)}
                            </div>
                            {#if path.announce_hash}
                                <div class="text-sem-fg-muted">
                                    <span class="font-semibold uppercase">{t("tools.rnpath.announce_hash")}:</span>
                                    {path.announce_hash}
                                </div>
                            {/if}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="danger-chip focus-ring-sem px-3 py-1.5 text-xs justify-center shrink-0"
                        onclick={() => onDropPath?.(path.hash)}
                    >
                        <MaterialDesignIcon iconName="link-variant-remove" class="size-3.5" />
                        {t("tools.rnpath.drop_path")}
                    </button>
                </div>
            {/each}
        </div>
    {/if}

    <!-- pagination -->
    {#if totalPages > 1}
        <div
            class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4"
        >
            <div class="flex items-center gap-2">
                <IconButton
                    disabled={currentPage === 1}
                    onclick={prevPage}
                    title={t("common.previous")}
                    class="size-9 min-w-9 min-h-9"
                >
                    <MaterialDesignIcon iconName="chevron-left" class="size-5" />
                </IconButton>
                <span class="text-sm font-medium text-sem-fg">
                    {t("tools.rnpath.page_of", { current: currentPage, total: totalPages })}
                </span>
                <IconButton
                    disabled={currentPage === totalPages}
                    onclick={nextPage}
                    title={t("common.next")}
                    class="size-9 min-w-9 min-h-9"
                >
                    <MaterialDesignIcon iconName="chevron-right" class="size-5" />
                </IconButton>
            </div>
            <div class="flex items-center gap-2 justify-between sm:justify-end w-full sm:w-auto">
                <span class="text-xs text-sem-fg-muted uppercase font-semibold">{t("tools.rnpath.show")}:</span>
                <select
                    value={itemsPerPage}
                    onchange={handleItemsPerPageChange}
                    class="bg-transparent border-none text-sm font-bold text-sem-fg focus:ring-0 cursor-pointer"
                >
                    {#each ITEMS_PER_PAGE_OPTIONS as option (option)}
                        <option value={option}>{option}</option>
                    {/each}
                </select>
            </div>
        </div>
    {/if}
</div>
