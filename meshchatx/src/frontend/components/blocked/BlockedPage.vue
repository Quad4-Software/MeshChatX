<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-linear-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
            <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
                <div
                    class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4"
                >
                    <div class="min-w-0 space-y-1">
                        <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
                            {{ $t("banishment.title") }}
                        </h1>
                        <p class="text-sm text-gray-600 dark:text-gray-400">
                            {{ $t("banishment.description") }}
                        </p>
                    </div>
                    <div class="flex items-center gap-2 sm:shrink-0">
                        <div class="relative flex-1 sm:w-64 lg:w-80">
                            <MaterialDesignIcon
                                icon-name="magnify"
                                class="absolute left-3 top-1/2 -translate-y-1/2 size-5 shrink-0 text-gray-400 pointer-events-none z-10"
                            />
                            <input
                                v-model="searchQuery"
                                type="text"
                                class="input-field pl-11!"
                                :placeholder="$t('banishment.search_placeholder')"
                                @input="onSearchInput"
                            />
                        </div>
                        <button
                            type="button"
                            class="secondary-chip p-2.5!"
                            :title="$t('common.refresh')"
                            @click="loadBlockedDestinations"
                        >
                            <MaterialDesignIcon
                                icon-name="refresh"
                                class="size-5"
                                :class="{ 'animate-spin-reverse': isLoading }"
                            />
                        </button>
                    </div>
                </div>

                <template v-if="isLoading && filteredBlockedIdentities.length === 0">
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 py-4 sm:py-6">
                        <div
                            v-for="i in 5"
                            :key="'skel-' + i"
                            class="banishment-card overflow-hidden p-5 space-y-4 min-w-0"
                        >
                            <div class="flex items-start gap-3">
                                <div class="size-10 rounded-xl bg-gray-200 dark:bg-zinc-700 animate-pulse shrink-0" />
                                <div class="flex-1 min-w-0 space-y-2">
                                    <div class="h-4 w-28 bg-gray-200 dark:bg-zinc-700 rounded-sm animate-pulse" />
                                    <div class="h-3 w-44 bg-gray-100 dark:bg-zinc-800 rounded-sm animate-pulse" />
                                </div>
                            </div>
                            <div class="space-y-1.5">
                                <div class="h-3 w-20 bg-gray-100 dark:bg-zinc-800 rounded-sm animate-pulse" />
                                <div class="h-8 bg-gray-100 dark:bg-zinc-800 rounded-lg animate-pulse" />
                            </div>
                            <div class="h-9 bg-gray-100 dark:bg-zinc-800 rounded-xl animate-pulse" />
                        </div>
                    </div>
                </template>

                <div
                    v-else-if="filteredBlockedIdentities.length === 0"
                    class="flex flex-col items-center justify-center py-16 sm:py-20 text-center"
                >
                    <div class="p-4 bg-gray-100 dark:bg-zinc-800 rounded-full mb-4 text-gray-400 dark:text-zinc-600">
                        <MaterialDesignIcon icon-name="check-circle" class="size-12" />
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                        {{ $t("banishment.no_items") }}
                    </h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400 max-w-sm mx-auto mt-1">
                        {{ searchQuery ? $t("nomadnet.no_search_results_peers") : $t("nomadnet.no_announces_yet") }}
                    </p>
                </div>

                <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 py-4 sm:py-6">
                    <div
                        v-for="identity in filteredBlockedIdentities"
                        :key="identity.identity_hash"
                        class="banishment-card overflow-hidden group min-w-0"
                    >
                        <div class="p-5 space-y-4">
                            <div class="flex items-start gap-3">
                                <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-xl shrink-0">
                                    <MaterialDesignIcon
                                        icon-name="account-off"
                                        class="size-5 text-red-600 dark:text-red-400"
                                    />
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="flex flex-wrap items-center gap-1.5 mb-1">
                                        <h3
                                            class="text-sm font-bold text-gray-900 dark:text-white truncate max-w-full"
                                            :title="identity.display_name || $t('call.unknown')"
                                        >
                                            {{ identity.display_name || $t("call.unknown") }}
                                        </h3>
                                        <span
                                            v-if="identity.is_node"
                                            class="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-[10px] font-bold uppercase tracking-wider shrink-0"
                                        >
                                            {{ $t("banishment.node") }}
                                        </span>
                                        <span
                                            v-else
                                            class="px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 text-[10px] font-bold uppercase tracking-wider shrink-0"
                                        >
                                            {{ $t("banishment.user") }}
                                        </span>
                                        <span
                                            v-if="identity.is_rns_blackholed"
                                            class="px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-[10px] font-bold uppercase tracking-wider border border-zinc-200 dark:border-zinc-700 shrink-0"
                                            title="Blackholed at Reticulum transport layer"
                                        >
                                            RNS Blackhole
                                        </span>
                                    </div>
                                    <p
                                        class="text-xs font-mono text-gray-500 dark:text-gray-400 truncate"
                                        :title="identity.identity_hash"
                                    >
                                        {{ identity.identity_hash }}
                                    </p>
                                </div>
                            </div>

                            <div v-if="identity.blocked_destinations.length > 0">
                                <p
                                    class="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-2 uppercase tracking-wide"
                                >
                                    {{ $t("banishment.blocked_destinations") }}
                                </p>
                                <div class="space-y-1">
                                    <div
                                        v-for="dest in identity.blocked_destinations"
                                        :key="dest.destination_hash"
                                        class="flex items-center justify-between gap-2 px-3 py-2 bg-gray-50 dark:bg-zinc-800/50 rounded-lg text-xs"
                                    >
                                        <span
                                            class="font-mono text-gray-500 dark:text-gray-400 truncate min-w-0"
                                            :title="dest.destination_hash"
                                        >
                                            {{ dest.destination_hash }}
                                        </span>
                                        <span v-if="dest.created_at" class="shrink-0 text-gray-400 dark:text-zinc-500">
                                            {{ formatTimeAgo(dest.created_at) }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="identity.rns_reason"
                                class="text-xs italic text-zinc-500 dark:text-zinc-400 leading-relaxed"
                            >
                                &ldquo;{{ identity.rns_reason }}&rdquo;
                            </div>
                            <div
                                v-if="identity.rns_source"
                                class="text-[10px] text-zinc-500 dark:text-zinc-500 font-mono truncate"
                            >
                                Source: {{ identity.rns_source }}
                            </div>

                            <button class="primary-chip w-full justify-center" @click="onUnblock(identity)">
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
        };
    },
    computed: {
        allBlockedIdentities() {
            return Object.values(this.blockedIdentities).sort((a, b) => {
                const nameA = (a.display_name || "").toLowerCase();
                const nameB = (b.display_name || "").toLowerCase();
                return nameA.localeCompare(nameB);
            });
        },
        filteredBlockedIdentities() {
            if (!this.searchQuery.trim()) {
                return this.allBlockedIdentities;
            }
            const query = this.searchQuery.toLowerCase();
            return this.allBlockedIdentities.filter((identity) => {
                if (identity.identity_hash.toLowerCase().includes(query)) return true;
                if ((identity.display_name || "").toLowerCase().includes(query)) return true;
                return identity.blocked_destinations.some((d) => d.destination_hash.toLowerCase().includes(query));
            });
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
                const targetHash =
                    identity.blocked_destinations.length > 0
                        ? identity.blocked_destinations[0].destination_hash
                        : identity.identity_hash;

                await window.api.delete(`/api/v1/blocked-destinations/${targetHash}`);
                await this.loadBlockedDestinations();
                ToastUtils.success(this.$t("banishment.banishment_lifted"));
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("banishment.failed_lift_banishment"));
            }
        },
        onSearchInput() {},
        formatTimeAgo(datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.banishment-card {
    @apply bg-white dark:bg-zinc-900/95 border border-gray-200/70 dark:border-zinc-800/80 rounded-2xl shadow-sm transition-all duration-200;
}
.banishment-card:hover {
    @apply shadow-md border-gray-300/80 dark:border-zinc-700/80;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-3 text-gray-900 dark:text-gray-100 transition;
}
</style>
