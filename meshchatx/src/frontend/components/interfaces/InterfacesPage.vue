<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full">
            <div class="p-3 md:p-6 space-y-4 w-full flex-1">
                <div
                    v-if="showRestartReminder"
                    class="bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-3xl shadow-xl p-4 flex flex-wrap gap-3 items-center"
                >
                    <div class="flex items-center gap-3">
                        <MaterialDesignIcon icon-name="alert" class="w-6 h-6" />
                        <div>
                            <div class="text-lg font-semibold">{{ $t("interfaces.restart_required") }}</div>
                            <div class="text-sm">{{ $t("interfaces.restart_description") }}</div>
                        </div>
                    </div>
                    <button
                        v-if="isElectron"
                        type="button"
                        class="ml-auto inline-flex items-center gap-2 rounded-full border border-white/40 px-4 py-1.5 text-sm font-semibold text-white hover:bg-white/10 transition"
                        @click="relaunch"
                    >
                        <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                        {{ $t("interfaces.restart_now") }}
                    </button>
                </div>

                <div class="glass-card space-y-4">
                    <div class="flex flex-wrap gap-3 items-center">
                        <div class="flex-1 min-w-0">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                {{ $t("interfaces.manage") }}
                            </div>
                            <div class="text-xl font-semibold text-gray-900 dark:text-white truncate">
                                {{ $t("interfaces.title") }}
                            </div>
                            <div class="text-sm text-gray-600 dark:text-gray-300">
                                {{ $t("interfaces.description") }}
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <RouterLink :to="{ name: 'interfaces.add' }" class="primary-chip px-4 py-2 text-sm">
                                <MaterialDesignIcon icon-name="plus" class="w-4 h-4" />
                                {{ $t("interfaces.add_interface") }}
                            </RouterLink>
                            <button type="button" class="secondary-chip text-sm" @click="showImportInterfacesModal">
                                <MaterialDesignIcon icon-name="import" class="w-4 h-4" />
                                {{ $t("interfaces.import") }}
                            </button>
                            <button type="button" class="secondary-chip text-sm" @click="exportInterfaces">
                                <MaterialDesignIcon icon-name="export" class="w-4 h-4" />
                                {{ $t("interfaces.export_all") }}
                            </button>
                            <!--
                        <button
                            type="button"
                            class="secondary-chip text-sm bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30"
                            :disabled="reloadingRns"
                            @click="reloadRns"
                        >
                            <MaterialDesignIcon
                                :icon-name="reloadingRns ? 'refresh' : 'restart'"
                                class="w-4 h-4"
                                :class="{ 'animate-spin-reverse': reloadingRns }"
                            />
                            {{ reloadingRns ? $t("app.reloading_rns") : $t("app.reload_rns") }}
                        </button>
                        --></div>
                    </div>
                    <div class="flex flex-wrap gap-3 items-center">
                        <div class="flex-1">
                            <input
                                v-model="searchTerm"
                                type="text"
                                :placeholder="$t('interfaces.search_placeholder')"
                                class="input-field"
                            />
                        </div>
                        <div class="flex gap-2 flex-wrap">
                            <button
                                type="button"
                                :class="filterChipClass(statusFilter === 'all')"
                                @click="setStatusFilter('all')"
                            >
                                {{ $t("interfaces.all") }}
                            </button>
                            <button
                                type="button"
                                :class="filterChipClass(statusFilter === 'enabled')"
                                @click="setStatusFilter('enabled')"
                            >
                                {{ $t("app.enabled") }}
                            </button>
                            <button
                                type="button"
                                :class="filterChipClass(statusFilter === 'disabled')"
                                @click="setStatusFilter('disabled')"
                            >
                                {{ $t("app.disabled") }}
                            </button>
                        </div>
                        <div class="w-full sm:w-60">
                            <select v-model="typeFilter" class="input-field">
                                <option value="all">{{ $t("interfaces.all_types") }}</option>
                                <option v-for="type in sortedInterfaceTypes" :key="type" :value="type">
                                    {{ type }}
                                </option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="glass-card space-y-4">
                    <div class="flex flex-wrap gap-2">
                        <button
                            v-for="tab in ['overview', 'discovery']"
                            :key="tab"
                            type="button"
                            :class="tabChipClass(activeTab === tab)"
                            @click="activeTab = tab"
                        >
                            <span v-if="tab === 'overview'">Overview</span>
                            <span v-else>Discovery Settings</span>
                        </button>
                    </div>

                    <div v-if="activeTab === 'overview'" class="space-y-4">
                        <div class="glass-card space-y-3">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                Configured
                            </div>
                            <div class="text-xl font-semibold text-gray-900 dark:text-white">Interfaces</div>
                            <div
                                v-if="filteredInterfaces.length !== 0"
                                class="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3 3xl:grid-cols-4 4xl:grid-cols-5"
                            >
                                <Interface
                                    v-for="iface of filteredInterfaces"
                                    :key="iface._name"
                                    :iface="iface"
                                    :is-reticulum-running="isReticulumRunning"
                                    @enable="enableInterface(iface._name)"
                                    @disable="disableInterface(iface._name)"
                                    @edit="editInterface(iface._name)"
                                    @export="exportInterface(iface._name)"
                                    @delete="deleteInterface(iface._name)"
                                />
                            </div>
                            <div v-else class="glass-card text-center py-10 text-gray-500 dark:text-gray-300">
                                <MaterialDesignIcon icon-name="lan-disconnect" class="w-10 h-10 mx-auto mb-3" />
                                <div class="text-lg font-semibold">{{ $t("interfaces.no_interfaces_found") }}</div>
                                <div class="text-sm">{{ $t("interfaces.no_interfaces_description") }}</div>
                            </div>
                        </div>

                        <div class="glass-card space-y-3">
                            <div class="flex items-center gap-3">
                                <div class="flex-1">
                                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                        Discovered Interfaces
                                    </div>
                                    <div class="text-xl font-semibold text-gray-900 dark:text-white">
                                        Recently Heard Announces
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-gray-300">
                                        Cards appear/disappear as announces are heard. Connected entries show a green
                                        pill; disconnected entries are dimmed with a red label.
                                    </div>
                                </div>
                                <div class="flex gap-2">
                                    <button
                                        v-if="interfacesWithLocation.length > 0"
                                        type="button"
                                        class="secondary-chip text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30"
                                        @click="mapAllDiscovered"
                                    >
                                        <MaterialDesignIcon icon-name="map-marker-multiple" class="w-4 h-4" />
                                        Map All ({{ interfacesWithLocation.length }})
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip text-xs"
                                        @click="loadDiscoveredInterfaces"
                                    >
                                        <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                                        Refresh
                                    </button>
                                </div>
                            </div>

                            <div
                                v-if="sortedDiscoveredInterfaces.length === 0"
                                class="text-sm text-gray-500 dark:text-gray-300"
                            >
                                No discovered interfaces yet.
                            </div>

                            <div
                                v-else
                                class="grid gap-4 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 4xl:grid-cols-6"
                            >
                                <div
                                    v-for="iface in sortedDiscoveredInterfaces"
                                    :key="iface.discovery_hash || iface.name"
                                    class="interface-card group transition-all duration-300"
                                    :class="{ 'opacity-70 grayscale-[0.3]': !isDiscoveredConnected(iface) }"
                                >
                                    <div class="flex gap-4 items-start relative">
                                        <!-- Disconnected Overlay -->
                                        <div
                                            v-if="!isDiscoveredConnected(iface)"
                                            class="absolute inset-0 z-10 flex items-center justify-center bg-white/20 dark:bg-zinc-900/20 backdrop-blur-[0.5px] rounded-3xl pointer-events-none"
                                        >
                                            <div
                                                class="bg-red-500/90 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider animate-pulse"
                                            >
                                                <MaterialDesignIcon icon-name="lan-disconnect" class="w-3.5 h-3.5" />
                                                <span>{{ $t("app.disabled") }}</span>
                                            </div>
                                        </div>

                                        <div class="interface-card__icon shrink-0">
                                            <MaterialDesignIcon :icon-name="getDiscoveryIcon(iface)" class="w-6 h-6" />
                                        </div>

                                        <div class="flex-1 min-w-0 space-y-2">
                                            <div class="flex items-center gap-2 flex-nowrap min-w-0">
                                                <div
                                                    class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate min-w-0"
                                                >
                                                    {{ iface.name }}
                                                </div>
                                                <span class="type-chip shrink-0">{{ iface.type }}</span>
                                            </div>

                                            <div class="flex items-center gap-2 flex-wrap">
                                                <span
                                                    v-if="iface.value"
                                                    class="text-[10px] font-bold text-blue-600 dark:text-blue-400"
                                                >
                                                    Stamps: {{ iface.value }}
                                                </span>
                                                <span
                                                    v-if="isDiscoveredConnected(iface)"
                                                    class="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-semibold dark:bg-emerald-900/40 dark:text-emerald-200 shrink-0"
                                                >
                                                    Connected
                                                </span>
                                            </div>

                                            <div class="flex flex-wrap gap-1.5 text-[10px] sm:text-xs">
                                                <span class="stat-chip bg-gray-50 dark:bg-zinc-800/50"
                                                    >Hops: {{ iface.hops }}</span
                                                >
                                                <span class="stat-chip capitalize bg-gray-50 dark:bg-zinc-800/50">{{
                                                    iface.status
                                                }}</span>
                                                <span
                                                    v-if="iface.last_heard"
                                                    class="stat-chip bg-gray-50 dark:bg-zinc-800/50"
                                                >
                                                    Heard: {{ formatLastHeard(iface.last_heard) }}
                                                </span>
                                            </div>

                                            <div class="grid gap-1.5 text-[10px] sm:text-[11px] pt-1 min-w-0">
                                                <div
                                                    v-if="iface.reachable_on"
                                                    class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                                                    @click="
                                                        copyToClipboard(
                                                            `${iface.reachable_on}:${iface.port}`,
                                                            'Address'
                                                        )
                                                    "
                                                >
                                                    <MaterialDesignIcon
                                                        icon-name="link-variant"
                                                        class="w-3.5 h-3.5 shrink-0"
                                                    />
                                                    <span class="truncate"
                                                        >Address: {{ iface.reachable_on }}:{{ iface.port }}</span
                                                    >
                                                </div>

                                                <div
                                                    v-if="iface.transport_id"
                                                    class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                                                    @click="copyToClipboard(iface.transport_id, 'Transport ID')"
                                                >
                                                    <MaterialDesignIcon
                                                        icon-name="identifier"
                                                        class="w-3.5 h-3.5 shrink-0"
                                                    />
                                                    <span class="truncate font-mono"
                                                        >Transport ID: {{ iface.transport_id }}</span
                                                    >
                                                </div>

                                                <div
                                                    v-if="iface.network_id"
                                                    class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                                                    @click="copyToClipboard(iface.network_id, 'Network ID')"
                                                >
                                                    <MaterialDesignIcon icon-name="lan" class="w-3.5 h-3.5 shrink-0" />
                                                    <span class="truncate font-mono"
                                                        >Network ID: {{ iface.network_id }}</span
                                                    >
                                                </div>

                                                <div
                                                    v-if="iface.latitude != null && iface.longitude != null"
                                                    class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                                                    @click="
                                                        copyToClipboard(
                                                            `${iface.latitude}, ${iface.longitude}`,
                                                            'Location'
                                                        )
                                                    "
                                                >
                                                    <MaterialDesignIcon
                                                        icon-name="map-marker"
                                                        class="w-3.5 h-3.5 shrink-0"
                                                    />
                                                    <span class="truncate"
                                                        >Loc: {{ iface.latitude }}, {{ iface.longitude }}</span
                                                    >
                                                </div>

                                                <div
                                                    v-if="discoveredBytes(iface)"
                                                    class="flex items-center gap-2 text-gray-500 dark:text-gray-500 min-w-0"
                                                >
                                                    <MaterialDesignIcon
                                                        icon-name="swap-vertical"
                                                        class="w-3.5 h-3.5 shrink-0"
                                                    />
                                                    <span class="truncate"
                                                        >TX {{ discoveredBytes(iface).tx }} · RX
                                                        {{ discoveredBytes(iface).rx }}</span
                                                    >
                                                </div>
                                            </div>
                                        </div>

                                        <div class="flex flex-col gap-2 shrink-0">
                                            <button
                                                v-if="iface.latitude != null && iface.longitude != null"
                                                type="button"
                                                class="secondary-chip !p-2 !rounded-xl"
                                                :title="$t('map.title')"
                                                @click="goToMap(iface)"
                                            >
                                                <MaterialDesignIcon icon-name="map" class="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-else class="space-y-4">
                        <div class="glass-card space-y-4">
                            <div class="flex flex-wrap gap-3 items-center">
                                <div class="flex-1">
                                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                        Discovery
                                    </div>
                                    <div class="text-xl font-semibold text-gray-900 dark:text-white">
                                        Interface Discovery
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-gray-300">
                                        Publish your interfaces for others to find, or listen for announced entrypoints
                                        and auto-connect to them.
                                    </div>
                                </div>
                                <RouterLink :to="{ name: 'interfaces.add' }" class="secondary-chip text-sm">
                                    <MaterialDesignIcon icon-name="lan" class="w-4 h-4" />
                                    Configure Per-Interface
                                </RouterLink>
                            </div>
                            <div class="grid gap-4 md:grid-cols-2">
                                <div class="space-y-2 text-sm text-gray-700 dark:text-gray-300">
                                    <div class="font-semibold text-gray-900 dark:text-white">Publish (Server)</div>
                                    <div>
                                        Enable discovery while adding or editing an interface to broadcast reachable
                                        details. Reticulum will sign and stamp announces automatically.
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400">
                                        Requires LXMF in the Python environment. Transport is optional for publishing,
                                        but usually recommended so peers can connect back.
                                    </div>
                                </div>
                                <div class="space-y-3">
                                    <div class="flex items-center">
                                        <div class="flex flex-col mr-auto">
                                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                Discover Interfaces (Peer)
                                            </div>
                                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                                Listen for discovery announces and optionally auto-connect to available
                                                interfaces.
                                            </div>
                                        </div>
                                        <Toggle v-model="discoveryConfig.discover_interfaces" class="my-auto mx-2" />
                                    </div>
                                    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                        <div>
                                            <div class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                                                Allowed Sources
                                            </div>
                                            <input
                                                v-model="discoveryConfig.interface_discovery_sources"
                                                type="text"
                                                placeholder="Comma separated identity hashes"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                                                Required Stamp Value
                                            </div>
                                            <input
                                                v-model.number="discoveryConfig.required_discovery_value"
                                                type="number"
                                                min="0"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                                                Auto-connect Slots
                                            </div>
                                            <input
                                                v-model.number="discoveryConfig.autoconnect_discovered_interfaces"
                                                type="number"
                                                min="0"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                                0 disables auto-connect.
                                            </div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                                                Network Identity Path
                                            </div>
                                            <input
                                                v-model="discoveryConfig.network_identity"
                                                type="text"
                                                placeholder="~/.reticulum/storage/identities/..."
                                                class="input-field"
                                            />
                                        </div>
                                    </div>
                                    <div class="flex justify-end">
                                        <button
                                            type="button"
                                            class="primary-chip text-xs"
                                            :disabled="savingDiscovery"
                                            @click="saveDiscoveryConfig"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="savingDiscovery ? 'progress-clock' : 'content-save'"
                                                class="w-4 h-4"
                                                :class="{ 'animate-spin-reverse': savingDiscovery }"
                                            />
                                            <span class="ml-1">Save Discovery Settings</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <ImportInterfacesModal ref="import-interfaces-modal" @dismissed="onImportInterfacesModalDismissed" />
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import ElectronUtils from "../../js/ElectronUtils";
import Interface from "./Interface.vue";
import Utils from "../../js/Utils";
import ImportInterfacesModal from "./ImportInterfacesModal.vue";
import DownloadUtils from "../../js/DownloadUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import GlobalState from "../../js/GlobalState";
import Toggle from "../forms/Toggle.vue";

export default {
    name: "InterfacesPage",
    components: {
        Toggle,
        ImportInterfacesModal,
        Interface,
        MaterialDesignIcon,
    },
    data() {
        return {
            interfaces: {},
            interfaceStats: {},
            reloadInterval: null,
            searchTerm: "",
            statusFilter: "all",
            typeFilter: "all",
            reloadingRns: false,
            isReticulumRunning: true,
            discoveryConfig: {
                discover_interfaces: false,
                interface_discovery_sources: "",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: 0,
                network_identity: "",
            },
            savingDiscovery: false,
            discoveredInterfaces: [],
            discoveredActive: [],
            discoveryInterval: null,
            activeTab: "overview",
        };
    },
    computed: {
        hasPendingInterfaceChanges() {
            return GlobalState.hasPendingInterfaceChanges;
        },
        modifiedInterfaceNames() {
            return GlobalState.modifiedInterfaceNames;
        },
        isElectron() {
            return ElectronUtils.isElectron();
        },
        showRestartReminder() {
            return this.hasPendingInterfaceChanges;
        },
        interfacesWithStats() {
            const results = [];
            for (const [interfaceName, iface] of Object.entries(this.interfaces)) {
                iface._name = interfaceName;
                iface._stats = this.interfaceStats[interfaceName];
                iface._restart_required = this.modifiedInterfaceNames.has(interfaceName);
                results.push(iface);
            }
            return results;
        },
        enabledInterfaces() {
            return this.interfacesWithStats.filter((iface) => this.isInterfaceEnabled(iface));
        },
        disabledInterfaces() {
            return this.interfacesWithStats.filter((iface) => !this.isInterfaceEnabled(iface));
        },
        filteredInterfaces() {
            const search = this.searchTerm.toLowerCase().trim();
            return this.interfacesWithStats
                .filter((iface) => {
                    if (this.statusFilter === "enabled" && !this.isInterfaceEnabled(iface)) {
                        return false;
                    }
                    if (this.statusFilter === "disabled" && this.isInterfaceEnabled(iface)) {
                        return false;
                    }
                    if (this.typeFilter !== "all" && iface.type !== this.typeFilter) {
                        return false;
                    }
                    if (!search) {
                        return true;
                    }
                    const haystack = [
                        iface._name,
                        iface.type,
                        iface.target_host,
                        iface.target_port,
                        iface.listen_ip,
                        iface.listen_port,
                    ]
                        .filter(Boolean)
                        .join(" ")
                        .toLowerCase();
                    return haystack.includes(search);
                })
                .sort((a, b) => {
                    const enabledDiff = Number(this.isInterfaceEnabled(b)) - Number(this.isInterfaceEnabled(a));
                    if (enabledDiff !== 0) return enabledDiff;
                    return a._name.localeCompare(b._name);
                });
        },
        sortedInterfaceTypes() {
            const types = new Set();
            this.interfacesWithStats.forEach((iface) => types.add(iface.type));
            return Array.from(types).sort();
        },
        sortedDiscoveredInterfaces() {
            return [...this.discoveredInterfaces].sort((a, b) => (b.last_heard || 0) - (a.last_heard || 0));
        },
        interfacesWithLocation() {
            return this.discoveredInterfaces.filter((iface) => iface.latitude != null && iface.longitude != null);
        },
        activeInterfaceStats() {
            return Object.values(this.interfaceStats || {});
        },
        tabChipClass() {
            return (isActive) => (isActive ? "primary-chip text-xs" : "secondary-chip text-xs");
        },
        discoveredActiveSet() {
            const set = new Set();
            this.discoveredActive.forEach((a) => {
                const host = a.target_host || a.remote || a.listen_ip;
                const port = a.target_port || a.listen_port;
                if (host && port) {
                    set.add(`${host}:${port}`);
                }
            });
            return set;
        },
        discoveredActiveTransportIds() {
            const set = new Set();
            this.discoveredActive.forEach((a) => {
                if (a.transport_id) {
                    set.add(a.transport_id);
                }
            });
            return set;
        },
    },
    beforeUnmount() {
        clearInterval(this.reloadInterval);
        clearInterval(this.discoveryInterval);
    },
    mounted() {
        this.loadInterfaces();
        this.updateInterfaceStats();
        this.loadDiscoveryConfig();
        this.loadDiscoveredInterfaces();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.updateInterfaceStats();
        }, 1000);

        this.discoveryInterval = setInterval(() => {
            this.loadDiscoveredInterfaces();
        }, 5000);
    },
    methods: {
        relaunch() {
            ElectronUtils.relaunch();
        },
        trackInterfaceChange(interfaceName = null) {
            GlobalState.hasPendingInterfaceChanges = true;
            if (interfaceName) {
                GlobalState.modifiedInterfaceNames.add(interfaceName);
            }
        },
        isInterfaceEnabled: function (iface) {
            return Utils.isInterfaceEnabled(iface);
        },
        async loadInterfaces() {
            try {
                const response = await window.axios.get(`/api/v1/reticulum/interfaces`);
                this.interfaces = response.data.interfaces;

                // also check app info for running state
                const appInfoResponse = await window.axios.get(`/api/v1/app/info`);
                this.isReticulumRunning = appInfoResponse.data.app_info.is_reticulum_running;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async updateInterfaceStats() {
            try {
                // fetch interface stats
                const response = await window.axios.get(`/api/v1/interface-stats`);

                // update data
                const interfaces = response.data.interface_stats?.interfaces ?? [];
                for (const iface of interfaces) {
                    this.interfaceStats[iface.short_name] = iface;
                }
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async enableInterface(interfaceName) {
            // enable interface
            try {
                await window.axios.post(`/api/v1/reticulum/interfaces/enable`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert("failed to enable interface");
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async disableInterface(interfaceName) {
            // disable interface
            try {
                await window.axios.post(`/api/v1/reticulum/interfaces/disable`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert("failed to disable interface");
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async editInterface(interfaceName) {
            this.$router.push({
                name: "interfaces.edit",
                query: {
                    interface_name: interfaceName,
                },
            });
        },
        async deleteInterface(interfaceName) {
            // ask user to confirm deleting conversation history
            if (
                !(await DialogUtils.confirm("Are you sure you want to delete this interface? This can not be undone!"))
            ) {
                return;
            }

            // delete interface
            try {
                await window.axios.post(`/api/v1/reticulum/interfaces/delete`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert("failed to delete interface");
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async exportInterfaces() {
            try {
                // fetch exported interfaces
                const response = await window.axios.post("/api/v1/reticulum/interfaces/export");

                // download file to browser
                DownloadUtils.downloadFile("meshchat_interfaces.txt", new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert("Failed to export interfaces");
                console.error(e);
            }
        },
        async exportInterface(interfaceName) {
            try {
                // fetch exported interfaces
                const response = await window.axios.post("/api/v1/reticulum/interfaces/export", {
                    selected_interface_names: [interfaceName],
                });

                // download file to browser
                DownloadUtils.downloadFile(`${interfaceName}.txt`, new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert("Failed to export interface");
                console.error(e);
            }
        },
        showImportInterfacesModal() {
            this.$refs["import-interfaces-modal"].show();
        },
        onImportInterfacesModalDismissed(imported = false) {
            // reload interfaces as something may have been imported
            this.loadInterfaces();
            if (imported) {
                this.trackInterfaceChange();
            }
        },
        async loadDiscoveredInterfaces() {
            try {
                const response = await window.axios.get(`/api/v1/reticulum/discovered-interfaces`);
                this.discoveredInterfaces = response.data?.interfaces ?? [];
                this.discoveredActive = response.data?.active ?? [];
            } catch (e) {
                console.log(e);
            }
        },
        formatLastHeard(ts) {
            const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
            if (seconds < 60) return `${seconds}s ago`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
            return `${Math.floor(seconds / 86400)}d ago`;
        },
        isDiscoveredConnected(iface) {
            const reach = iface.reachable_on;
            const port = iface.port;
            if (iface.transport_id && this.discoveredActiveTransportIds.has(iface.transport_id)) {
                return true;
            }
            if (reach && port && this.discoveredActiveSet && this.discoveredActiveSet.has(`${reach}:${port}`)) {
                return true;
            }
            return this.activeInterfaceStats.some((s) => {
                const hostMatch =
                    (s.target_host && reach && s.target_host === reach) || (s.remote && reach && s.remote === reach);
                const portMatch =
                    (s.target_port && port && Number(s.target_port) === Number(port)) ||
                    (s.listen_port && port && Number(s.listen_port) === Number(port));
                return hostMatch && portMatch && (s.connected || s.online);
            });
        },
        goToMap(iface) {
            if (iface.latitude == null || iface.longitude == null) return;
            this.$router.push({
                name: "map",
                query: {
                    lat: iface.latitude,
                    lon: iface.longitude,
                    label: iface.name,
                },
            });
        },
        mapAllDiscovered() {
            this.$router.push({
                name: "map",
                query: { view: "discovered" },
            });
        },
        discoveredBytes(iface) {
            const reach = iface.reachable_on;
            const port = iface.port;
            const stats = this.activeInterfaceStats || [];
            const match = stats.find((s) => {
                const host = s.target_host || s.remote || s.interface_name;
                const p = s.target_port || s.listen_port;
                const hostMatch = host && reach && host === reach;
                const portMatch = p && port && Number(p) === Number(port);
                return hostMatch && portMatch;
            });
            if (!match) return null;
            return {
                tx: this.formatBytes(match.txb || 0),
                rx: this.formatBytes(match.rxb || 0),
            };
        },
        formatBytes(bytes) {
            return Utils.formatBytes(bytes || 0);
        },
        parseBool(value) {
            if (typeof value === "string") {
                return ["true", "yes", "1", "y", "on"].includes(value.toLowerCase());
            }
            return Boolean(value);
        },
        async loadDiscoveryConfig() {
            try {
                const response = await window.axios.get(`/api/v1/reticulum/discovery`);
                const discovery = response.data?.discovery ?? {};
                this.discoveryConfig.discover_interfaces = this.parseBool(discovery.discover_interfaces);
                this.discoveryConfig.interface_discovery_sources = discovery.interface_discovery_sources ?? "";
                this.discoveryConfig.required_discovery_value =
                    discovery.required_discovery_value !== undefined &&
                    discovery.required_discovery_value !== null &&
                    discovery.required_discovery_value !== ""
                        ? Number(discovery.required_discovery_value)
                        : null;
                this.discoveryConfig.autoconnect_discovered_interfaces =
                    discovery.autoconnect_discovered_interfaces !== undefined &&
                    discovery.autoconnect_discovered_interfaces !== null &&
                    discovery.autoconnect_discovered_interfaces !== ""
                        ? Number(discovery.autoconnect_discovered_interfaces)
                        : 0;
                this.discoveryConfig.network_identity = discovery.network_identity ?? "";
            } catch (e) {
                console.log(e);
            }
        },
        async saveDiscoveryConfig() {
            if (this.savingDiscovery) return;
            this.savingDiscovery = true;
            try {
                const payload = {
                    discover_interfaces: this.discoveryConfig.discover_interfaces,
                    interface_discovery_sources: this.discoveryConfig.interface_discovery_sources || null,
                    required_discovery_value:
                        this.discoveryConfig.required_discovery_value === null ||
                        this.discoveryConfig.required_discovery_value === ""
                            ? null
                            : Number(this.discoveryConfig.required_discovery_value),
                    autoconnect_discovered_interfaces:
                        this.discoveryConfig.autoconnect_discovered_interfaces === null ||
                        this.discoveryConfig.autoconnect_discovered_interfaces === ""
                            ? 0
                            : Number(this.discoveryConfig.autoconnect_discovered_interfaces),
                    network_identity: this.discoveryConfig.network_identity || null,
                };

                await window.axios.patch(`/api/v1/reticulum/discovery`, payload);
                ToastUtils.success("Discovery settings saved");
                await this.loadDiscoveryConfig();
            } catch (e) {
                ToastUtils.error("Failed to save discovery settings");
                console.log(e);
            } finally {
                this.savingDiscovery = false;
            }
        },
        getDiscoveryIcon(iface) {
            switch (iface.type) {
                case "AutoInterface":
                    return "home-automation";
                case "RNodeInterface":
                    return iface.port && iface.port.toString().startsWith("tcp://") ? "lan-connect" : "radio-tower";
                case "RNodeMultiInterface":
                    return "access-point-network";
                case "TCPClientInterface":
                case "BackboneInterface":
                    return "lan-connect";
                case "TCPServerInterface":
                    return "lan";
                case "UDPInterface":
                    return "wan";
                case "SerialInterface":
                    return "usb-port";
                case "KISSInterface":
                case "AX25KISSInterface":
                    return "antenna";
                case "I2PInterface":
                    return "eye";
                case "PipeInterface":
                    return "pipe";
                default:
                    return "server-network";
            }
        },
        copyToClipboard(text, label) {
            if (!text) return;
            navigator.clipboard.writeText(text);
            ToastUtils.success(`${label} copied to clipboard`);
        },
        setStatusFilter(value) {
            this.statusFilter = value;
        },
        filterChipClass(isActive) {
            return isActive ? "primary-chip text-xs" : "secondary-chip text-xs";
        },
        async reloadRns() {
            if (this.reloadingRns) return;

            try {
                this.reloadingRns = true;
                const response = await window.axios.post("/api/v1/reticulum/reload");
                ToastUtils.success(response.data.message);
                GlobalState.hasPendingInterfaceChanges = false;
                GlobalState.modifiedInterfaceNames.clear();
                await this.loadInterfaces();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || "Failed to reload Reticulum!");
                console.error(e);
            } finally {
                this.reloadingRns = false;
            }
        },
    },
};
</script>
