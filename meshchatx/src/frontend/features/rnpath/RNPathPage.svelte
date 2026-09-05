<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import { t } from "../../js/i18n.js";
    import { DEFAULT_REMOTE_TIMEOUT, DEFAULT_ITEMS_PER_PAGE, RNPATH_TABS } from "./lib/constants.js";
    import { buildPathQueryParams, buildRemoteQueryParams, extractInterfaceNames } from "./lib/pathQuery.js";
    import type { PathEntry, RateEntry, RNPathTab, PathTableResponse } from "./lib/types.js";
    import RNPathTableTab from "./components/RNPathTableTab.svelte";
    import RNPathRatesTab from "./components/RNPathRatesTab.svelte";
    import RNPathActionsTab from "./components/RNPathActionsTab.svelte";

    let tab = $state<RNPathTab>("table");
    let isLoading = $state(false);
    let pathTable = $state<PathEntry[]>([]);
    let rateTable = $state<RateEntry[]>([]);
    let interfaces = $state<string[]>([]);

    let searchQuery = $state("");
    let filterInterface = $state("");
    let filterHops = $state<number | string | null>(null);
    let currentPage = $state(1);
    let itemsPerPage = $state(DEFAULT_ITEMS_PER_PAGE);
    let totalItems = $state(0);
    let responsiveItems = $state(0);
    let unresponsiveItems = $state(0);

    let remoteHash = $state("");
    let identityPath = $state("");
    let remoteTimeout = $state(DEFAULT_REMOTE_TIMEOUT);
    let activeRemoteHash = $state("");

    const totalPages = $derived(Math.max(1, Math.ceil(totalItems / itemsPerPage)));

    async function fetchPathTableData(): Promise<PathTableResponse> {
        let params: Record<string, unknown>;
        try {
            params = buildPathQueryParams({
                searchQuery,
                filterInterface,
                filterHops,
                currentPage,
                itemsPerPage,
                remoteHash,
                identityPath,
                remoteTimeout,
            });
        } catch {
            throw new Error(t("tools.rnpath.invalid_hops"));
        }
        const res: any = await window.api.get("/api/v1/rnpath/table", { params });
        return (res?.data || { table: [], total: 0, responsive: 0, unresponsive: 0 }) as PathTableResponse;
    }

    export async function refreshAll(): Promise<void> {
        isLoading = true;
        try {
            const remoteParams = buildRemoteQueryParams(remoteHash, identityPath, remoteTimeout);
            const [pathRes, rateRes, ifaceRes, discRes]: any = await Promise.all([
                fetchPathTableData(),
                window.api.get("/api/v1/rnpath/rates", { params: remoteParams }),
                window.api.get("/api/v1/reticulum/interfaces"),
                window.api.get("/api/v1/reticulum/discovered-interfaces").catch(() => ({ data: {} })),
            ]);
            pathTable = pathRes?.table || [];
            totalItems = pathRes?.total || 0;
            responsiveItems = pathRes?.responsive || 0;
            unresponsiveItems = pathRes?.unresponsive || 0;
            activeRemoteHash = pathRes?.remote || rateRes?.data?.remote || "";
            rateTable = rateRes?.data?.rates || [];
            interfaces = extractInterfaceNames(ifaceRes?.data, discRes?.data);
        } catch (e: any) {
            console.error(e);
            const detail = e?.response?.data?.message || e?.message || "";
            ToastUtils.error(detail ? `${t("tools.rnpath.failed_fetch")}: ${detail}` : t("tools.rnpath.failed_fetch"));
        } finally {
            isLoading = false;
        }
    }

    export async function refreshTable(): Promise<void> {
        isLoading = true;
        try {
            const res = await fetchPathTableData();
            pathTable = res.table || [];
            totalItems = res.total || 0;
            responsiveItems = res.responsive || 0;
            unresponsiveItems = res.unresponsive || 0;
            activeRemoteHash = res.remote || "";
        } catch (e: any) {
            console.error(e);
            const detail = e?.response?.data?.message || e?.message || "";
            ToastUtils.error(detail ? `${t("tools.rnpath.failed_fetch")}: ${detail}` : t("tools.rnpath.failed_fetch"));
        } finally {
            isLoading = false;
        }
    }

    function handleFilterChange(): void {
        currentPage = 1;
        refreshTable();
    }

    function handlePageChange(page: number): void {
        currentPage = page;
        refreshTable();
    }

    function clearRemote(): void {
        remoteHash = "";
        activeRemoteHash = "";
        refreshAll();
    }

    async function dropPath(hash: string): Promise<void> {
        if (!(await DialogUtils.confirm(t("tools.rnpath.drop_confirm", { hash })))) {
            return;
        }
        try {
            const res: any = await window.api.post("/api/v1/rnpath/drop", { destination_hash: hash });
            if (res?.data?.success) {
                ToastUtils.success(t("tools.rnpath.path_dropped"));
                refreshAll();
            } else {
                ToastUtils.error(t("tools.rnpath.failed_drop"));
            }
        } catch {
            ToastUtils.error(t("tools.rnpath.error_drop"));
        }
    }

    async function requestPath(hash: string): Promise<void> {
        try {
            await window.api.post("/api/v1/rnpath/request", { destination_hash: hash });
            ToastUtils.success(t("tools.rnpath.path_requested", { hash: hash.substring(0, 8) }));
        } catch {
            ToastUtils.error(t("tools.rnpath.failed_request"));
        }
    }

    async function dropAllVia(hash: string): Promise<void> {
        if (!(await DialogUtils.confirm(t("tools.rnpath.drop_via_confirm", { hash })))) {
            return;
        }
        try {
            const res: any = await window.api.post("/api/v1/rnpath/drop-via", {
                transport_instance_hash: hash,
            });
            if (res?.data?.success) {
                ToastUtils.success(t("tools.rnpath.paths_dropped"));
                refreshAll();
            }
        } catch {
            ToastUtils.error(t("tools.rnpath.failed_drop_paths"));
        }
    }

    async function dropAnnounceQueues(): Promise<void> {
        if (!(await DialogUtils.confirm(t("tools.rnpath.purge_confirm")))) {
            return;
        }
        try {
            await window.api.post("/api/v1/rnpath/drop-queues");
            ToastUtils.success(t("tools.rnpath.queues_purged"));
        } catch {
            ToastUtils.error(t("tools.rnpath.failed_purge"));
        }
    }

    onMount(() => {
        refreshAll();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="rnpath-page">
    <ToolsPageHeader
        icon="route"
        title={t("tools.rnpath.title")}
        description={t("tools.rnpath.description")}
        accent="indigo"
    >
        <button
            type="button"
            class="p-2 text-gray-500 hover:text-indigo-500 dark:text-gray-400 dark:hover:text-indigo-400 transition-colors cursor-pointer"
            title="Refresh"
            onclick={refreshAll}
        >
            <MaterialDesignIcon iconName="refresh" class="size-6 {isLoading ? 'animate-spin-reverse' : ''}" />
        </button>
    </ToolsPageHeader>

    <div
        class="flex-1 overflow-y-auto min-w-0 p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6 pb-[max(1rem,env(safe-area-inset-bottom))]"
    >
        <!-- tabs -->
        <div class="-mx-3 sm:mx-0 overflow-x-auto border-b border-sem-border">
            <div class="flex min-w-0 px-3 sm:px-0">
                {#each RNPATH_TABS as tName (tName)}
                    <button
                        type="button"
                        class="shrink-0 px-4 sm:px-6 py-3 text-sm font-semibold transition-colors border-b-2 -mb-px cursor-pointer {tab ===
                        tName
                            ? 'text-indigo-600 border-indigo-500 dark:text-indigo-400 dark:border-indigo-400'
                            : 'text-gray-500 border-transparent hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
                        onclick={() => (tab = tName)}
                    >
                        {tName.charAt(0).toUpperCase() + tName.slice(1)}
                    </button>
                {/each}
            </div>
        </div>

        {#if tab === "table"}
            <RNPathTableTab
                {pathTable}
                {totalItems}
                {responsiveItems}
                {unresponsiveItems}
                {interfaces}
                {totalPages}
                bind:remoteHash
                bind:identityPath
                bind:remoteTimeout
                {activeRemoteHash}
                bind:searchQuery
                bind:filterInterface
                bind:filterHops
                bind:currentPage
                bind:itemsPerPage
                onDropPath={dropPath}
                onClearRemote={clearRemote}
                onFilterChange={handleFilterChange}
                onPageChange={handlePageChange}
            />
        {:else if tab === "rates"}
            <RNPathRatesTab {rateTable} />
        {:else if tab === "actions"}
            <RNPathActionsTab
                onRequestPath={requestPath}
                onDropAllVia={dropAllVia}
                onDropAnnounceQueues={dropAnnounceQueues}
            />
        {/if}
    </div>
</div>
