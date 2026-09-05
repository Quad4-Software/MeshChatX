<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import EmptyState from "../../ui/svelte/EmptyState.svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import Utils from "../../js/Utils.js";
    import { t } from "../../js/i18n.js";
    import { filterBlockedIdentities, identityBlockedAt } from "./lib/blockedList.js";
    import type { BlockedIdentity } from "./lib/blockedList.js";

    interface BlockedDestinationEntry {
        destination_hash: string;
        created_at: string | null;
    }

    interface BlockedIdentityItem extends BlockedIdentity {
        identity_hash: string;
        display_name: string | null;
        is_node: boolean;
        blocked_destinations: BlockedDestinationEntry[];
        is_rns_blackholed: boolean;
        rns_source: string | null;
        rns_reason: string | null;
        rns_until: string | null;
    }

    interface BlackholeEntry {
        source?: string;
        reason?: string;
        until?: string;
    }

    let blockedIdentities = $state<Record<string, BlockedIdentityItem>>({});
    let isLoading = $state(false);
    let searchQuery = $state("");
    let selectMode = $state(false);
    let selectedIdentities = $state<string[]>([]);
    let typeFilter = $state("all");
    let dateSort = $state("newest");

    const allBlockedIdentities = $derived(Object.values(blockedIdentities));
    const filteredBlockedIdentities = $derived(
        filterBlockedIdentities(allBlockedIdentities, { searchQuery, typeFilter, dateSort }) as BlockedIdentityItem[]
    );
    const isAllSelected = $derived(
        filteredBlockedIdentities.length > 0 &&
            filteredBlockedIdentities.every((identity) => selectedIdentities.includes(identity.identity_hash))
    );

    async function loadBlockedDestinations(): Promise<void> {
        isLoading = true;
        try {
            const response = await window.api.get("/api/v1/blocked-destinations");
            const blockedHashes: Array<{ destination_hash: string; created_at?: string | null }> =
                response.data.blocked_destinations || [];

            let reticulumBlackholed: Record<string, BlackholeEntry> = {};
            try {
                const rnsResponse = await window.api.get("/api/v1/reticulum/blackhole");
                reticulumBlackholed = rnsResponse.data.blackholed_identities || {};
            } catch (e) {
                console.error("Failed to load Reticulum blackhole", e);
            }

            const identityMap: Record<string, BlockedIdentityItem> = {};

            const ensureIdentity = (identityHash: string): BlockedIdentityItem => {
                if (!identityMap[identityHash]) {
                    identityMap[identityHash] = {
                        identity_hash: identityHash,
                        display_name: null,
                        is_node: false,
                        blocked_destinations: [],
                        is_rns_blackholed: false,
                        rns_source: null,
                        rns_reason: null,
                        rns_until: null,
                    };
                }
                return identityMap[identityHash];
            };

            const processBlockedHash = async (blocked: { destination_hash: string; created_at?: string | null }) => {
                const hash = blocked.destination_hash;
                let identityHash = hash;
                let displayName: string | null = null;
                let isNode = false;

                try {
                    const announceResponse = await window.api.get("/api/v1/announces", {
                        params: {
                            destination_hash: hash,
                            include_blocked: true,
                            limit: 1,
                        },
                    });

                    if (announceResponse.data.announces && announceResponse.data.announces.length > 0) {
                        const announce = announceResponse.data.announces[0];
                        identityHash = announce.identity_hash || hash;
                        displayName = announce.display_name || null;
                        isNode = announce.aspect === "nomadnetwork.node";
                    }
                } catch {
                    // ignore error
                }

                const identity = ensureIdentity(identityHash);
                identity.display_name = identity.display_name || displayName;
                identity.is_node = identity.is_node || isNode;
                identity.blocked_destinations.push({
                    destination_hash: hash,
                    created_at: blocked.created_at || null,
                });
            };

            await Promise.all(blockedHashes.map((blocked) => processBlockedHash(blocked)));

            for (const [hash, info] of Object.entries(reticulumBlackholed)) {
                const identity = ensureIdentity(hash);
                identity.is_rns_blackholed = true;
                identity.rns_source = info.source || null;
                identity.rns_reason = info.reason || null;
                identity.rns_until = info.until || null;

                if (!identity.display_name) {
                    try {
                        const announceResponse = await window.api.get("/api/v1/announces", {
                            params: {
                                identity_hash: hash,
                                include_blocked: true,
                                limit: 1,
                            },
                        });
                        if (announceResponse.data.announces && announceResponse.data.announces.length > 0) {
                            const announce = announceResponse.data.announces[0];
                            identity.display_name = announce.display_name || null;
                            identity.is_node = announce.aspect === "nomadnetwork.node";
                        }
                    } catch {
                        // ignore
                    }
                }
            }

            blockedIdentities = identityMap;
        } catch (e) {
            console.log(e);
            ToastUtils.error(t("banishment.failed_load_banished"));
        } finally {
            isLoading = false;
        }
    }

    async function unblockIdentity(identity: BlockedIdentityItem): Promise<void> {
        const targetHash =
            identity.blocked_destinations.length > 0
                ? identity.blocked_destinations[0].destination_hash
                : identity.identity_hash;
        await window.api.delete(`/api/v1/blocked-destinations/${targetHash}`);
    }

    async function onUnblock(identity: BlockedIdentityItem): Promise<void> {
        if (
            !(await DialogUtils.confirm(
                t("banishment.lift_banishment_confirm", {
                    name: identity.display_name || identity.identity_hash,
                })
            ))
        ) {
            return;
        }

        try {
            await unblockIdentity(identity);
            await loadBlockedDestinations();
            ToastUtils.success(t("banishment.banishment_lifted"));
        } catch (e) {
            console.log(e);
            ToastUtils.error(t("banishment.failed_lift_banishment"));
        }
    }

    async function onUnblockSelected(): Promise<void> {
        if (selectedIdentities.length === 0) {
            return;
        }
        if (!(await DialogUtils.confirm(t("banishment.lift_selected_confirm", { count: selectedIdentities.length })))) {
            return;
        }

        const selected = allBlockedIdentities.filter((identity) => selectedIdentities.includes(identity.identity_hash));
        let lifted = 0;
        for (const identity of selected) {
            try {
                await unblockIdentity(identity);
                lifted += 1;
            } catch (e) {
                console.log(e);
            }
        }

        exitSelectMode();
        await loadBlockedDestinations();
        if (lifted > 0) {
            ToastUtils.success(t("banishment.lift_selected_success", { count: lifted }));
        }
        if (lifted < selected.length) {
            ToastUtils.error(t("banishment.failed_lift_banishment"));
        }
    }

    function toggleSelectAll(): void {
        if (isAllSelected) {
            selectedIdentities = [];
            return;
        }
        selectedIdentities = filteredBlockedIdentities.map((identity) => identity.identity_hash);
    }

    function exitSelectMode(): void {
        selectMode = false;
        selectedIdentities = [];
    }

    function toggleSelected(hash: string, checked: boolean): void {
        if (checked) {
            if (!selectedIdentities.includes(hash)) {
                selectedIdentities = [...selectedIdentities, hash];
            }
            return;
        }
        selectedIdentities = selectedIdentities.filter((h) => h !== hash);
    }

    onMount(() => {
        loadBlockedDestinations();
    });
</script>

<div class="flex min-w-0 flex-1 flex-col overflow-hidden bg-sem-canvas text-sem-fg" data-testid="blocked-page">
    <div class="flex-1 overflow-x-hidden overflow-y-auto px-3 py-3 sm:px-5 sm:py-4 min-w-0">
        <div class="mx-auto w-full max-w-6xl min-w-0 space-y-0 xl:max-w-7xl">
            <div
                class="flex w-full flex-col gap-3 border-b border-sem-border py-3 sm:flex-row sm:items-start sm:justify-between sm:py-4"
            >
                <div class="min-w-0 space-y-1">
                    <h1 class="text-xl font-semibold tracking-tight sm:text-2xl">
                        {t("banishment.title")}
                    </h1>
                    <p class="text-sm text-sem-fg-muted">
                        {t("banishment.description")}
                    </p>
                </div>
                <div class="flex items-center gap-2 sm:shrink-0">
                    <div class="relative min-w-0 flex-1 sm:w-64 lg:w-80">
                        <span
                            class="pointer-events-none absolute left-2.5 top-1/2 z-10 size-4 shrink-0 -translate-y-1/2 text-sem-fg-muted"
                        >
                            <MaterialDesignIcon iconName="magnify" />
                        </span>
                        <input
                            bind:value={searchQuery}
                            type="text"
                            class="w-full rounded-full border-0 bg-sem-surface-muted py-2 pl-9 pr-3 text-sm text-sem-fg outline-hidden ring-1 ring-sem-border/50 focus:ring-sem-accent/40"
                            placeholder={t("banishment.search_placeholder")}
                        />
                    </div>
                    {#if !selectMode}
                        <button
                            type="button"
                            class="shrink-0 rounded-lg px-2 py-2 text-xs font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                            onclick={() => (selectMode = true)}
                        >
                            {t("common.select")}
                        </button>
                    {:else}
                        <label class="flex shrink-0 cursor-pointer items-center gap-2">
                            <input
                                type="checkbox"
                                class="rounded border-sem-border text-sem-accent focus:ring-sem-accent/30"
                                checked={isAllSelected}
                                onchange={toggleSelectAll}
                            />
                            <span class="text-xs text-sem-fg-muted">{t("archives.select_all")}</span>
                        </label>
                        {#if selectedIdentities.length > 0}
                            <button
                                type="button"
                                class="shrink-0 rounded-lg px-2 py-2 text-xs font-medium text-sem-accent transition-colors hover:bg-sem-surface/60"
                                onclick={onUnblockSelected}
                            >
                                {t("banishment.lift_selected", { count: selectedIdentities.length })}
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="shrink-0 rounded-lg px-2 py-2 text-xs font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                            onclick={exitSelectMode}
                        >
                            {t("common.cancel")}
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="inline-flex size-9 shrink-0 items-center justify-center rounded-[10px] text-sem-fg-muted transition hover:bg-sem-surface/60 hover:text-sem-fg"
                        title={t("common.refresh")}
                        onclick={loadBlockedDestinations}
                    >
                        <span class={isLoading ? "animate-spin-reverse inline-flex" : "inline-flex"}>
                            <MaterialDesignIcon iconName="refresh" />
                        </span>
                    </button>
                </div>
            </div>

            {#if !isLoading || filteredBlockedIdentities.length > 0}
                <div class="flex flex-wrap items-center gap-2 border-b border-sem-border/40 py-2">
                    <select
                        bind:value={typeFilter}
                        class="rounded-full border-0 bg-sem-surface-muted px-3 py-1.5 text-xs text-sem-fg outline-hidden ring-1 ring-sem-border/50 focus:ring-sem-accent/40"
                    >
                        <option value="all">{t("banishment.filter_all_types")}</option>
                        <option value="user">{t("banishment.user")}</option>
                        <option value="node">{t("banishment.node")}</option>
                        <option value="rns">{t("banishment.filter_rns")}</option>
                    </select>
                    <select
                        bind:value={dateSort}
                        class="rounded-full border-0 bg-sem-surface-muted px-3 py-1.5 text-xs text-sem-fg outline-hidden ring-1 ring-sem-border/50 focus:ring-sem-accent/40"
                    >
                        <option value="newest">{t("banishment.sort_newest")}</option>
                        <option value="oldest">{t("banishment.sort_oldest")}</option>
                        <option value="name">{t("banishment.sort_name")}</option>
                    </select>
                    {#if filteredBlockedIdentities.length > 0}
                        <span class="text-xs text-sem-fg-muted">
                            {t("banishment.result_count", { count: filteredBlockedIdentities.length })}
                        </span>
                    {/if}
                </div>
            {/if}

            {#if isLoading && filteredBlockedIdentities.length === 0}
                <div class="grid grid-cols-1 gap-3 py-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {#each [1, 2, 3, 4, 5] as i (i)}
                        <div class="min-h-[9.5rem] rounded-xl bg-sem-surface/40 p-3">
                            <div class="flex items-start gap-2">
                                <div class="size-8 shrink-0 animate-pulse bg-sem-surface-muted"></div>
                                <div class="min-w-0 flex-1 space-y-2">
                                    <div class="h-3.5 w-28 animate-pulse rounded-sm bg-sem-surface-muted"></div>
                                    <div class="h-3 w-full animate-pulse rounded-sm bg-sem-surface-muted/70"></div>
                                </div>
                            </div>
                            <div class="mt-3 h-8 animate-pulse bg-sem-surface-muted/70"></div>
                        </div>
                    {/each}
                </div>
            {:else if filteredBlockedIdentities.length === 0}
                <div class="py-12 sm:py-16">
                    <EmptyState
                        icon="check-circle"
                        title={t("banishment.no_items")}
                        description={searchQuery
                            ? t("nomadnet.no_search_results_peers")
                            : t("nomadnet.no_announces_yet")}
                    />
                </div>
            {:else}
                <div class="grid grid-cols-1 gap-3 py-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {#each filteredBlockedIdentities as identity (identity.identity_hash)}
                        {@const selected = selectMode && selectedIdentities.includes(identity.identity_hash)}
                        <div
                            class="flex min-h-[9.5rem] min-w-0 flex-col rounded-xl bg-sem-surface/35 transition-colors hover:bg-sem-surface/55 {selected
                                ? 'ring-1 ring-sem-accent/50'
                                : ''}"
                        >
                            <div class="flex min-h-0 flex-1 flex-col gap-2.5 p-3">
                                <div class="flex min-w-0 items-start gap-2">
                                    {#if selectMode}
                                        <div class="flex shrink-0 items-center pt-0.5">
                                            <input
                                                type="checkbox"
                                                class="rounded border-sem-border text-sem-accent focus:ring-sem-accent/30"
                                                checked={selectedIdentities.includes(identity.identity_hash)}
                                                onchange={(e) =>
                                                    toggleSelected(identity.identity_hash, e.currentTarget.checked)}
                                            />
                                        </div>
                                    {/if}
                                    <div
                                        class="flex size-8 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted"
                                    >
                                        <MaterialDesignIcon iconName="account-off" />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="mb-1 flex min-w-0 items-center gap-1.5">
                                            <h3
                                                class="min-w-0 flex-1 truncate text-sm font-semibold"
                                                title={identity.display_name || t("call.unknown")}
                                            >
                                                {identity.display_name || t("call.unknown")}
                                            </h3>
                                            {#if identity.is_node}
                                                <span
                                                    class="shrink-0 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sem-accent"
                                                >
                                                    {t("banishment.node")}
                                                </span>
                                            {:else}
                                                <span
                                                    class="shrink-0 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted"
                                                >
                                                    {t("banishment.user")}
                                                </span>
                                            {/if}
                                        </div>
                                        <p
                                            class="truncate font-mono text-xs text-sem-fg-muted"
                                            title={identity.identity_hash}
                                        >
                                            {identity.identity_hash}
                                        </p>
                                        {#if identityBlockedAt(identity)}
                                            <p class="mt-0.5 text-[11px] text-sem-fg-muted">
                                                {t("banishment.banished_at")}
                                                {Utils.formatTimeAgo(identityBlockedAt(identity))}
                                            </p>
                                        {/if}
                                        {#if identity.is_rns_blackholed}
                                            <span
                                                class="mt-1 inline-block truncate text-[10px] font-medium uppercase tracking-wide text-sem-fg-muted"
                                                title="Blackholed at Reticulum transport layer"
                                            >
                                                RNS Blackhole
                                            </span>
                                        {/if}
                                    </div>
                                </div>

                                {#if identity.blocked_destinations.length > 0}
                                    <div class="min-w-0">
                                        <p
                                            class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted"
                                        >
                                            {t("banishment.blocked_destinations")}
                                        </p>
                                        <div class="max-h-20 space-y-1 overflow-y-auto">
                                            {#each identity.blocked_destinations as dest (dest.destination_hash)}
                                                <div
                                                    class="flex min-w-0 items-center justify-between gap-2 rounded-md bg-sem-surface-muted/70 px-2 py-1 text-xs"
                                                >
                                                    <span
                                                        class="min-w-0 truncate font-mono text-sem-fg-muted"
                                                        title={dest.destination_hash}
                                                    >
                                                        {dest.destination_hash}
                                                    </span>
                                                    {#if dest.created_at}
                                                        <span class="shrink-0 text-[10px] text-sem-fg-muted">
                                                            {Utils.formatTimeAgo(dest.created_at)}
                                                        </span>
                                                    {/if}
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                {/if}

                                {#if identity.rns_reason}
                                    <div class="truncate text-xs italic text-sem-fg-muted" title={identity.rns_reason}>
                                        &ldquo;{identity.rns_reason}&rdquo;
                                    </div>
                                {/if}
                                {#if identity.rns_source}
                                    <div
                                        class="truncate font-mono text-[10px] text-sem-fg-muted"
                                        title={identity.rns_source}
                                    >
                                        Source: {identity.rns_source}
                                    </div>
                                {/if}

                                {#if !selectMode}
                                    <button
                                        type="button"
                                        class="mt-auto inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-sem-accent/15 px-3 py-2 text-sm font-medium text-sem-accent transition hover:bg-sem-accent/25"
                                        onclick={() => onUnblock(identity)}
                                    >
                                        <MaterialDesignIcon iconName="check-circle" />
                                        <span>{t("banishment.lift_banishment")}</span>
                                    </button>
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
</div>
