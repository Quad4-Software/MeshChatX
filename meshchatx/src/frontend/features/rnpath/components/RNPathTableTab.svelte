<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ManagementIdentityPicker from "./ManagementIdentityPicker.svelte";
    import { t } from "../../../js/i18n.js";
    import { getStateColor, getStateText, formatDate } from "../lib/pathQuery.js";
    import { ITEMS_PER_PAGE_OPTIONS } from "../lib/constants.js";
    import type { PathEntry } from "../lib/types.js";

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
    }: {
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
    } = $props();

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
                placeholder="Search Hash or Via..."
                class="input-field pr-10"
                autocomplete="off"
            />
            <MaterialDesignIcon
                iconName="magnify"
                class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-gray-400"
            />
        </div>
        <select value={filterInterface} onchange={handleInterfaceChange} class="input-field">
            <option value="">All Interfaces</option>
            {#each interfaces as iface (iface)}
                <option value={iface}>
                    {iface}
                </option>
            {/each}
        </select>
        <div class="flex items-center gap-2">
            <span class="text-xs font-semibold text-gray-500 uppercase min-w-fit">Hops:</span>
            <input
                value={filterHops ?? ""}
                oninput={handleHopsInput}
                type="number"
                min="0"
                max="128"
                placeholder="Any"
                class="input-field"
            />
        </div>
        <div
            class="flex flex-wrap items-center justify-start sm:justify-end gap-x-4 gap-y-2 sm:flex-nowrap lg:col-span-1"
        >
            <div class="flex flex-col items-start sm:items-end">
                <span class="text-[10px] font-bold text-gray-400 uppercase">Total</span>
                <span class="text-sm font-bold">{totalItems}</span>
            </div>
            <div class="flex flex-col items-start sm:items-end">
                <span class="text-[10px] font-bold text-green-500 uppercase">Responsive</span>
                <span class="text-sm font-bold text-green-600 dark:text-green-400">{responsiveItems}</span>
            </div>
            <div class="flex flex-col items-start sm:items-end">
                <span class="text-[10px] font-bold text-red-500 uppercase">Unresponsive</span>
                <span class="text-sm font-bold text-red-600 dark:text-red-400">{unresponsiveItems}</span>
            </div>
        </div>
    </div>

    {#if pathTable.length === 0}
        <div class="rounded-lg border border-sem-border bg-sem-surface p-8 sm:p-12 text-center text-gray-500">
            No paths found matching your criteria.
        </div>
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
                            <div class="text-gray-400">
                                <span class="font-semibold uppercase">Last Updated:</span>
                                {path.timestamp ? formatDate(path.timestamp) : "Unknown"}
                            </div>
                            <div class="text-gray-400">
                                <span class="font-semibold uppercase">Expires:</span>
                                {formatDate(path.expires)}
                            </div>
                            {#if path.announce_hash}
                                <div class="text-gray-400">
                                    <span class="font-semibold uppercase">Announce Hash:</span>
                                    {path.announce_hash}
                                </div>
                            {/if}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-red-200 dark:border-red-900/30 cursor-pointer"
                        onclick={() => onDropPath?.(path.hash)}
                    >
                        Drop Path
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
                <button
                    type="button"
                    class="p-2 rounded-lg hover:bg-sem-surface-muted disabled:opacity-50 transition-colors cursor-pointer disabled:cursor-not-allowed"
                    disabled={currentPage === 1}
                    onclick={prevPage}
                    title="Previous page"
                >
                    <MaterialDesignIcon iconName="chevron-left" class="size-5" />
                </button>
                <span class="text-sm font-medium"> Page {currentPage} of {totalPages} </span>
                <button
                    type="button"
                    class="p-2 rounded-lg hover:bg-sem-surface-muted disabled:opacity-50 transition-colors cursor-pointer disabled:cursor-not-allowed"
                    disabled={currentPage === totalPages}
                    onclick={nextPage}
                    title="Next page"
                >
                    <MaterialDesignIcon iconName="chevron-right" class="size-5" />
                </button>
            </div>
            <div class="flex items-center gap-2 justify-between sm:justify-end w-full sm:w-auto">
                <span class="text-xs text-gray-500 uppercase font-semibold">Show:</span>
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
