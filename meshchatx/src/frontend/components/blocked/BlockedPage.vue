<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex min-w-0 flex-1 flex-col overflow-hidden bg-sem-canvas text-sem-fg">
        <div class="flex-1 overflow-x-hidden overflow-y-auto px-3 py-3 sm:px-5 sm:py-4 min-w-0">
            <div class="mx-auto w-full max-w-6xl min-w-0 space-y-0 xl:max-w-7xl">
                <div
                    class="flex w-full flex-col gap-3 border-b border-sem-border py-3 sm:flex-row sm:items-start sm:justify-between sm:py-4"
                >
                    <div class="min-w-0 space-y-1">
                        <h1 class="text-xl font-semibold tracking-tight sm:text-2xl">
                            {{ $t("banishment.title") }}
                        </h1>
                        <p class="text-sm text-sem-fg-muted">
                            {{ $t("banishment.description") }}
                        </p>
                    </div>
                    <div class="flex items-center gap-2 sm:shrink-0">
                        <div class="relative min-w-0 flex-1 sm:w-64 lg:w-80">
                            <MaterialDesignIcon
                                icon-name="magnify"
                                class="pointer-events-none absolute left-2.5 top-1/2 z-10 size-4 shrink-0 -translate-y-1/2 text-sem-fg-muted"
                            />
                            <input
                                v-model="searchQuery"
                                type="text"
                                class="w-full rounded-full border-0 bg-sem-surface-muted py-2 pl-9 pr-3 text-sm text-sem-fg outline-none ring-1 ring-sem-border/50 focus:ring-sem-accent/40"
                                :placeholder="$t('banishment.search_placeholder')"
                                @input="onSearchInput"
                            />
                        </div>
                        <button
                            v-if="!selectMode"
                            type="button"
                            class="shrink-0 rounded-lg px-2 py-2 text-xs font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                            @click="selectMode = true"
                        >
                            {{ $t("common.select") }}
                        </button>
                        <template v-else>
                            <label class="flex shrink-0 cursor-pointer items-center gap-2">
                                <input
                                    type="checkbox"
                                    class="rounded border-sem-border text-sem-accent focus:ring-sem-accent/30"
                                    :checked="isAllSelected"
                                    @change="toggleSelectAll"
                                />
                                <span class="text-xs text-sem-fg-muted">{{ $t("archives.select_all") }}</span>
                            </label>
                            <button
                                v-if="selectedIdentities.length > 0"
                                type="button"
                                class="shrink-0 rounded-lg px-2 py-2 text-xs font-medium text-sem-accent transition-colors hover:bg-sem-surface/60"
                                @click="onUnblockSelected"
                            >
                                {{ $t("banishment.lift_selected", { count: selectedIdentities.length }) }}
                            </button>
                            <button
                                type="button"
                                class="shrink-0 rounded-lg px-2 py-2 text-xs font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                                @click="exitSelectMode"
                            >
                                {{ $t("common.cancel") }}
                            </button>
                        </template>
                        <button
                            type="button"
                            class="inline-flex size-9 shrink-0 items-center justify-center rounded-[10px] text-sem-fg-muted transition hover:bg-sem-surface/60 hover:text-sem-fg"
                            :title="$t('common.refresh')"
                            @click="loadBlockedDestinations"
                        >
                            <MaterialDesignIcon
                                icon-name="refresh"
                                class="size-4"
                                :class="{ 'animate-spin-reverse': isLoading }"
                            />
                        </button>
                    </div>
                </div>

                <div
                    v-if="!isLoading || filteredBlockedIdentities.length > 0"
                    class="flex flex-wrap items-center gap-2 border-b border-sem-border/40 py-2"
                >
                    <select
                        v-model="typeFilter"
                        class="rounded-full border-0 bg-sem-surface-muted px-3 py-1.5 text-xs text-sem-fg outline-none ring-1 ring-sem-border/50 focus:ring-sem-accent/40"
                    >
                        <option value="all">{{ $t("banishment.filter_all_types") }}</option>
                        <option value="user">{{ $t("banishment.user") }}</option>
                        <option value="node">{{ $t("banishment.node") }}</option>
                        <option value="rns">{{ $t("banishment.filter_rns") }}</option>
                    </select>
                    <select
                        v-model="dateSort"
                        class="rounded-full border-0 bg-sem-surface-muted px-3 py-1.5 text-xs text-sem-fg outline-none ring-1 ring-sem-border/50 focus:ring-sem-accent/40"
                    >
                        <option value="newest">{{ $t("banishment.sort_newest") }}</option>
                        <option value="oldest">{{ $t("banishment.sort_oldest") }}</option>
                        <option value="name">{{ $t("banishment.sort_name") }}</option>
                    </select>
                    <span v-if="filteredBlockedIdentities.length > 0" class="text-xs text-sem-fg-muted">
                        {{ $t("banishment.result_count", { count: filteredBlockedIdentities.length }) }}
                    </span>
                </div>

                <template v-if="isLoading && filteredBlockedIdentities.length === 0">
                    <div class="grid grid-cols-1 gap-3 py-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        <div v-for="i in 5" :key="'skel-' + i" class="min-h-[9.5rem] rounded-xl bg-sem-surface/40 p-3">
                            <div class="flex items-start gap-2">
                                <div class="size-8 shrink-0 animate-pulse bg-sem-surface-muted" />
                                <div class="min-w-0 flex-1 space-y-2">
                                    <div class="h-3.5 w-28 animate-pulse rounded-sm bg-sem-surface-muted" />
                                    <div class="h-3 w-full animate-pulse rounded-sm bg-sem-surface-muted/70" />
                                </div>
                            </div>
                            <div class="mt-3 h-8 animate-pulse bg-sem-surface-muted/70" />
                        </div>
                    </div>
                </template>

                <div
                    v-else-if="filteredBlockedIdentities.length === 0"
                    class="flex flex-col items-center justify-center py-16 text-center sm:py-20"
                >
                    <div class="mb-4 rounded-full bg-sem-surface-muted p-4 text-sem-fg-muted">
                        <MaterialDesignIcon icon-name="check-circle" class="size-10" />
                    </div>
                    <h3 class="text-lg font-semibold">
                        {{ $t("banishment.no_items") }}
                    </h3>
                    <p class="mx-auto mt-1 max-w-sm text-sm text-sem-fg-muted">
                        {{ searchQuery ? $t("nomadnet.no_search_results_peers") : $t("nomadnet.no_announces_yet") }}
                    </p>
                </div>

                <div v-else class="grid grid-cols-1 gap-3 py-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    <div
                        v-for="identity in filteredBlockedIdentities"
                        :key="identity.identity_hash"
                        class="flex min-h-[9.5rem] min-w-0 flex-col rounded-xl bg-sem-surface/35 transition-colors hover:bg-sem-surface/55"
                        :class="{
                            'ring-1 ring-sem-accent/50':
                                selectMode && selectedIdentities.includes(identity.identity_hash),
                        }"
                    >
                        <div class="flex min-h-0 flex-1 flex-col gap-2.5 p-3">
                            <div class="flex min-w-0 items-start gap-2">
                                <div v-if="selectMode" class="flex shrink-0 items-center pt-0.5" @click.stop>
                                    <input
                                        v-model="selectedIdentities"
                                        type="checkbox"
                                        class="rounded border-sem-border text-sem-accent focus:ring-sem-accent/30"
                                        :value="identity.identity_hash"
                                    />
                                </div>
                                <div
                                    class="flex size-8 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted"
                                >
                                    <MaterialDesignIcon icon-name="account-off" class="size-4 text-red-500" />
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div class="mb-1 flex min-w-0 items-center gap-1.5">
                                        <h3
                                            class="min-w-0 flex-1 truncate text-sm font-semibold"
                                            :title="identity.display_name || $t('call.unknown')"
                                        >
                                            {{ identity.display_name || $t("call.unknown") }}
                                        </h3>
                                        <span
                                            v-if="identity.is_node"
                                            class="shrink-0 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sem-accent"
                                        >
                                            {{ $t("banishment.node") }}
                                        </span>
                                        <span
                                            v-else
                                            class="shrink-0 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted"
                                        >
                                            {{ $t("banishment.user") }}
                                        </span>
                                    </div>
                                    <p
                                        class="truncate font-mono text-xs text-sem-fg-muted"
                                        :title="identity.identity_hash"
                                    >
                                        {{ identity.identity_hash }}
                                    </p>
                                    <p v-if="identityBlockedAt(identity)" class="mt-0.5 text-[11px] text-sem-fg-muted">
                                        {{ $t("banishment.banished_at") }}
                                        {{ formatTimeAgo(identityBlockedAt(identity)) }}
                                    </p>
                                    <span
                                        v-if="identity.is_rns_blackholed"
                                        class="mt-1 inline-block truncate text-[10px] font-medium uppercase tracking-wide text-sem-fg-muted"
                                        title="Blackholed at Reticulum transport layer"
                                    >
                                        RNS Blackhole
                                    </span>
                                </div>
                            </div>

                            <div v-if="identity.blocked_destinations.length > 0" class="min-w-0">
                                <p class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted">
                                    {{ $t("banishment.blocked_destinations") }}
                                </p>
                                <div class="max-h-20 space-y-1 overflow-y-auto">
                                    <div
                                        v-for="dest in identity.blocked_destinations"
                                        :key="dest.destination_hash"
                                        class="flex min-w-0 items-center justify-between gap-2 rounded-md bg-sem-surface-muted/70 px-2 py-1 text-xs"
                                    >
                                        <span
                                            class="min-w-0 truncate font-mono text-sem-fg-muted"
                                            :title="dest.destination_hash"
                                        >
                                            {{ dest.destination_hash }}
                                        </span>
                                        <span v-if="dest.created_at" class="shrink-0 text-[10px] text-sem-fg-muted">
                                            {{ formatTimeAgo(dest.created_at) }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="identity.rns_reason"
                                class="truncate text-xs italic text-sem-fg-muted"
                                :title="identity.rns_reason"
                            >
                                &ldquo;{{ identity.rns_reason }}&rdquo;
                            </div>
                            <div
                                v-if="identity.rns_source"
                                class="truncate font-mono text-[10px] text-sem-fg-muted"
                                :title="identity.rns_source"
                            >
                                Source: {{ identity.rns_source }}
                            </div>

                            <button
                                v-if="!selectMode"
                                type="button"
                                class="mt-auto inline-flex w-full items-center justify-center gap-1.5 rounded-full bg-sem-accent/15 px-3 py-2 text-sm font-medium text-sem-accent transition hover:bg-sem-accent/25"
                                @click="onUnblock(identity)"
                            >
                                <MaterialDesignIcon icon-name="check-circle" class="size-4" />
                                <span>{{ $t("banishment.lift_banishment") }}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import Utils from "../../js/Utils";

export default {
    name: "BlockedPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            blockedIdentities: {},
            isLoading: false,
            searchQuery: "",
            selectMode: false,
            selectedIdentities: [],
            typeFilter: "all",
            dateSort: "newest",
        };
    },
    computed: {
        allBlockedIdentities() {
            return Object.values(this.blockedIdentities);
        },
        filteredBlockedIdentities() {
            let list = [...this.allBlockedIdentities];
            const query = this.searchQuery.trim().toLowerCase();
            if (query) {
                list = list.filter((identity) => {
                    if (identity.identity_hash.toLowerCase().includes(query)) return true;
                    if ((identity.display_name || "").toLowerCase().includes(query)) return true;
                    return identity.blocked_destinations.some((d) => d.destination_hash.toLowerCase().includes(query));
                });
            }

            if (this.typeFilter === "user") {
                list = list.filter((identity) => !identity.is_node && !identity.is_rns_blackholed);
            } else if (this.typeFilter === "node") {
                list = list.filter((identity) => identity.is_node);
            } else if (this.typeFilter === "rns") {
                list = list.filter((identity) => identity.is_rns_blackholed);
            }

            if (this.dateSort === "name") {
                list.sort((a, b) => {
                    const nameA = (a.display_name || a.identity_hash).toLowerCase();
                    const nameB = (b.display_name || b.identity_hash).toLowerCase();
                    return nameA.localeCompare(nameB);
                });
            } else if (this.dateSort === "oldest") {
                list.sort((a, b) => this.compareBlockedAt(a, b));
            } else {
                list.sort((a, b) => this.compareBlockedAt(b, a));
            }

            return list;
        },
        isAllSelected() {
            if (this.filteredBlockedIdentities.length === 0) {
                return false;
            }
            return this.filteredBlockedIdentities.every((identity) =>
                this.selectedIdentities.includes(identity.identity_hash)
            );
        },
    },
    mounted() {
        this.loadBlockedDestinations();
    },
    methods: {
        async loadBlockedDestinations() {
            this.isLoading = true;
            try {
                const response = await window.api.get("/api/v1/blocked-destinations");
                const blockedHashes = response.data.blocked_destinations || [];

                let reticulumBlackholed = {};
                try {
                    const rnsResponse = await window.api.get("/api/v1/reticulum/blackhole");
                    reticulumBlackholed = rnsResponse.data.blackholed_identities || {};
                } catch (e) {
                    console.error("Failed to load Reticulum blackhole", e);
                }

                const identityMap = {};

                const ensureIdentity = (identityHash) => {
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

                const processBlockedHash = async (blocked) => {
                    const hash = blocked.destination_hash;
                    let identityHash = hash;
                    let displayName = null;
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

                this.blockedIdentities = identityMap;
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("banishment.failed_load_banished"));
            } finally {
                this.isLoading = false;
            }
        },
        async onUnblock(identity) {
            if (
                !(await DialogUtils.confirm(
                    this.$t("banishment.lift_banishment_confirm", {
                        name: identity.display_name || identity.identity_hash,
                    })
                ))
            ) {
                return;
            }

            try {
                await this.unblockIdentity(identity);
                await this.loadBlockedDestinations();
                ToastUtils.success(this.$t("banishment.banishment_lifted"));
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("banishment.failed_lift_banishment"));
            }
        },
        async onUnblockSelected() {
            if (this.selectedIdentities.length === 0) {
                return;
            }
            if (
                !(await DialogUtils.confirm(
                    this.$t("banishment.lift_selected_confirm", { count: this.selectedIdentities.length })
                ))
            ) {
                return;
            }

            const selected = this.allBlockedIdentities.filter((identity) =>
                this.selectedIdentities.includes(identity.identity_hash)
            );
            let lifted = 0;
            for (const identity of selected) {
                try {
                    await this.unblockIdentity(identity);
                    lifted += 1;
                } catch (e) {
                    console.log(e);
                }
            }

            this.exitSelectMode();
            await this.loadBlockedDestinations();
            if (lifted > 0) {
                ToastUtils.success(this.$t("banishment.lift_selected_success", { count: lifted }));
            }
            if (lifted < selected.length) {
                ToastUtils.error(this.$t("banishment.failed_lift_banishment"));
            }
        },
        async unblockIdentity(identity) {
            const targetHash =
                identity.blocked_destinations.length > 0
                    ? identity.blocked_destinations[0].destination_hash
                    : identity.identity_hash;
            await window.api.delete(`/api/v1/blocked-destinations/${targetHash}`);
        },
        toggleSelectAll() {
            if (this.isAllSelected) {
                this.selectedIdentities = [];
                return;
            }
            this.selectedIdentities = this.filteredBlockedIdentities.map((identity) => identity.identity_hash);
        },
        exitSelectMode() {
            this.selectMode = false;
            this.selectedIdentities = [];
        },
        onSearchInput() {},
        identityBlockedAt(identity) {
            const dates = identity.blocked_destinations.map((dest) => dest.created_at).filter(Boolean);
            if (dates.length === 0) {
                return null;
            }
            return dates.sort().reverse()[0];
        },
        compareBlockedAt(a, b) {
            const atA = this.identityBlockedAt(a) || "";
            const atB = this.identityBlockedAt(b) || "";
            if (atA === atB) {
                const nameA = (a.display_name || a.identity_hash).toLowerCase();
                const nameB = (b.display_name || b.identity_hash).toLowerCase();
                return nameA.localeCompare(nameB);
            }
            return atA.localeCompare(atB);
        },
        formatTimeAgo(datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
    },
};
</script>
