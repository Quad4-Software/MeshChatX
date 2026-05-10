<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 h-full overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <div
            class="flex items-center px-4 py-4 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 shadow-xs"
        >
            <div class="flex items-center gap-3">
                <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                    <MaterialDesignIcon icon-name="gavel" class="size-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">{{ $t("banishment.title") }}</h1>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{{ $t("banishment.description") }}</p>
                </div>
            </div>

            <div class="ml-auto flex items-center gap-2 sm:gap-4">
                <div class="relative w-32 sm:w-64 md:w-80">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                        :placeholder="$t('banishment.search_placeholder')"
                        @input="onSearchInput"
                    />
                </div>
                <button
                    class="p-2 text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
                    :title="$t('common.refresh')"
                    @click="loadBlockedDestinations"
                >
                    <MaterialDesignIcon
                        icon-name="refresh"
                        class="size-6"
                        :class="{ 'animate-spin-reverse': isLoading }"
                    />
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4 md:p-6">
            <div
                v-if="isLoading && filteredBlockedIdentities.length === 0"
                class="flex flex-col items-center justify-center h-64"
            >
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
                <p class="text-gray-500 dark:text-gray-400">{{ $t("banishment.loading_items") }}</p>
            </div>

            <div
                v-else-if="filteredBlockedIdentities.length === 0"
                class="flex flex-col items-center justify-center h-64 text-center"
            >
                <div class="p-4 bg-gray-100 dark:bg-zinc-800 rounded-full mb-4 text-gray-400 dark:text-zinc-600">
                    <MaterialDesignIcon icon-name="check-circle" class="size-12" />
                </div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white">{{ $t("banishment.no_items") }}</h3>
                <p class="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                    {{ searchQuery ? $t("nomadnet.no_search_results_peers") : $t("nomadnet.no_announces_yet") }}
                </p>
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div
                    v-for="identity in filteredBlockedIdentities"
                    :key="identity.identity_hash"
                    class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl shadow-lg overflow-hidden"
                >
                    <div class="p-5">
                        <div class="flex items-start justify-between mb-4">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 mb-2">
                                    <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg shrink-0">
                                        <MaterialDesignIcon
                                            icon-name="account-off"
                                            class="size-5 text-red-600 dark:text-red-400"
                                        />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="flex items-center gap-2 mb-1 flex-wrap">
                                            <h4
                                                class="text-base font-semibold text-gray-900 dark:text-white wrap-break-word"
                                                :title="identity.display_name"
                                            >
                                                {{ identity.display_name || $t("call.unknown") }}
                                            </h4>
                                            <span
                                                v-if="identity.is_node"
                                                class="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-sm"
                                            >
                                                {{ $t("banishment.node") }}
                                            </span>
                                            <span
                                                v-else
                                                class="px-2 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-sm"
                                            >
                                                {{ $t("banishment.user") }}
                                            </span>
                                            <span
                                                v-if="identity.is_rns_blackholed"
                                                class="px-2 py-0.5 text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-sm border border-zinc-200 dark:border-zinc-700"
                                                title="Blackholed at Reticulum transport layer"
                                            >
                                                RNS Blackhole
                                            </span>
                                        </div>
                                        <p
                                            class="text-xs text-gray-500 dark:text-gray-400 font-mono break-all mt-1"
                                            :title="identity.identity_hash"
                                        >
                                            {{ identity.identity_hash }}
                                        </p>
                                    </div>
                                </div>

                                <!-- Blocked destination hashes -->
                                <div v-if="identity.blocked_destinations.length > 0" class="mb-2">
                                    <p class="text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
                                        {{ $t("banishment.blocked_destinations") }}
                                    </p>
                                    <div class="space-y-1">
                                        <div
                                            v-for="dest in identity.blocked_destinations"
                                            :key="dest.destination_hash"
                                            class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 font-mono bg-gray-50 dark:bg-zinc-800 px-2 py-1 rounded"
                                        >
                                            <span class="break-all">{{ dest.destination_hash }}</span>
                                            <span
                                                v-if="dest.created_at"
                                                class="shrink-0 ml-2 text-gray-400 dark:text-zinc-500"
                                            >
                                                {{ formatTimeAgo(dest.created_at) }}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    v-if="identity.rns_reason"
                                    class="text-xs italic text-zinc-500 dark:text-zinc-400 mb-2"
                                >
                                    "{{ identity.rns_reason }}"
                                </div>
                                <div
                                    v-if="identity.rns_source"
                                    class="text-[10px] text-zinc-500 dark:text-zinc-500 font-mono truncate mb-1"
                                >
                                    Source: {{ identity.rns_source }}
                                </div>
                            </div>
                        </div>
                        <button
                            class="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors font-medium"
                            @click="onUnblock(identity)"
                        >
                            <MaterialDesignIcon icon-name="check-circle" class="size-5" />
                            <span>{{ $t("banishment.lift_banishment") }}</span>
                        </button>
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
                // Load local blocked destinations
                const response = await window.api.get("/api/v1/blocked-destinations");
                const blockedHashes = response.data.blocked_destinations || [];

                // Load Reticulum blackholed identities
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

                // Process local blocked destinations
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

                // Process Reticulum blackholed identities
                for (const [hash, info] of Object.entries(reticulumBlackholed)) {
                    const identity = ensureIdentity(hash);
                    identity.is_rns_blackholed = true;
                    identity.rns_source = info.source || null;
                    identity.rns_reason = info.reason || null;
                    identity.rns_until = info.until || null;

                    // Try to look up display name from announces
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
                // Use the first blocked destination hash, or fall back to identity hash
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
