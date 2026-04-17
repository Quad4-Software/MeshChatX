<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6">
            <div class="space-y-0 w-full min-w-0 max-w-6xl xl:max-w-7xl 2xl:max-w-[90rem] mx-auto flex-1">
                <div
                    v-if="showRestartReminder"
                    class="bg-amber-600 text-white border border-amber-500/30 p-4 sm:rounded-xl flex flex-wrap gap-3 items-center mb-4 sm:mb-6"
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

                <div
                    class="interfaces-section interfaces-section--hero flex flex-col lg:flex-row lg:items-center justify-between gap-6"
                >
                    <div class="space-y-3 flex-1 min-w-0">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("interfaces.manage") }}
                        </div>
                        <div class="text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                            {{ $t("interfaces.title") }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed max-w-xl">
                            {{ $t("interfaces.description") }}
                        </div>
                        <div class="flex flex-wrap gap-2 pt-2">
                            <RouterLink
                                :to="{ name: 'interfaces.add' }"
                                class="primary-chip px-4 py-2 text-sm min-h-[44px] sm:min-h-0 items-center justify-center inline-flex"
                            >
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
                            <button
                                type="button"
                                class="secondary-chip text-sm"
                                :disabled="reloadingRns"
                                @click="reloadRns"
                            >
                                <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                                <span>{{ reloadingRns ? $t("app.reloading_rns") : "Restart RNS" }}</span>
                            </button>
                        </div>
                    </div>

                    <div class="w-full md:w-96 shrink-0 space-y-4">
                        <div class="relative group">
                            <MaterialDesignIcon
                                icon-name="magnify"
                                class="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors"
                            />
                            <input
                                v-model="searchTerm"
                                type="text"
                                :placeholder="$t('interfaces.search_placeholder')"
                                class="w-full pl-12 pr-4 py-3 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 shadow-sm"
                            />
                            <button
                                v-if="searchTerm"
                                class="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                                @click="searchTerm = ''"
                            >
                                <MaterialDesignIcon icon-name="close-circle" class="size-5" />
                            </button>
                        </div>
                        <div>
                            <select
                                v-model="typeFilter"
                                class="w-full px-4 py-2.5 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-gray-900 dark:text-white"
                            >
                                <option value="all">{{ $t("interfaces.all_types") }}</option>
                                <option v-for="type in sortedInterfaceTypes" :key="type" :value="type">
                                    {{ type }}
                                </option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="interfaces-section space-y-4">
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
                        <div class="interfaces-subpanel space-y-3">
                            <div class="flex flex-wrap items-center justify-between gap-4">
                                <div class="space-y-1">
                                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                        Configured
                                    </div>
                                    <div class="text-xl font-semibold text-gray-900 dark:text-white">
                                        Interfaces
                                        <span
                                            v-if="filteredInterfaces.length > 0"
                                            class="ml-2 text-sm font-medium text-gray-400"
                                            >({{ filteredInterfaces.length }})</span
                                        >
                                    </div>
                                </div>
                                <div class="flex gap-2 flex-wrap">
                                    <button
                                        type="button"
                                        :class="filterChipClass(statusFilter === 'all')"
                                        class="!py-1 !px-3"
                                        @click="setStatusFilter('all')"
                                    >
                                        {{ $t("interfaces.all") }}
                                    </button>
                                    <button
                                        type="button"
                                        :class="filterChipClass(statusFilter === 'enabled')"
                                        class="!py-1 !px-3"
                                        @click="setStatusFilter('enabled')"
                                    >
                                        {{ $t("app.enabled") }}
                                    </button>
                                    <button
                                        type="button"
                                        :class="filterChipClass(statusFilter === 'disabled')"
                                        class="!py-1 !px-3"
                                        @click="setStatusFilter('disabled')"
                                    >
                                        {{ $t("app.disabled") }}
                                    </button>
                                </div>
                            </div>
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
                            <div
                                v-else
                                class="text-center py-10 px-4 text-gray-500 dark:text-gray-300 border border-dashed border-gray-200 dark:border-zinc-800 rounded-xl"
                            >
                                <MaterialDesignIcon icon-name="lan-disconnect" class="w-10 h-10 mx-auto mb-3" />
                                <div class="text-lg font-semibold">{{ $t("interfaces.no_interfaces_found") }}</div>
                                <div class="text-sm">{{ $t("interfaces.no_interfaces_description") }}</div>
                            </div>
                        </div>

                        <div class="interfaces-subpanel space-y-3">
                            <div class="flex flex-col gap-3 min-w-0 lg:flex-row lg:items-start lg:justify-between">
                                <div class="min-w-0 flex-1">
                                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                        Discovered Interfaces
                                    </div>
                                    <div class="text-xl font-semibold text-gray-900 dark:text-white">
                                        Recently Heard Announces
                                        <span
                                            v-if="sortedDiscoveredInterfaces.length > 0"
                                            class="ml-2 text-sm font-medium text-gray-400"
                                            >({{ sortedDiscoveredInterfaces.length }})</span
                                        >
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-gray-300">
                                        Discovery runs continually; heard announces stay listed. Connected entries show
                                        a green pill; disconnected entries are dimmed with a red label.
                                    </div>
                                </div>
                                <div class="flex flex-wrap gap-2 items-center shrink-0 min-w-0">
                                    <div class="flex gap-1.5 mr-2">
                                        <button
                                            type="button"
                                            :class="filterChipClass(discoveredStatusFilter === 'all')"
                                            class="!py-1 !px-3"
                                            @click="discoveredStatusFilter = 'all'"
                                        >
                                            {{ $t("interfaces.all") }}
                                        </button>
                                        <button
                                            type="button"
                                            :class="filterChipClass(discoveredStatusFilter === 'connected')"
                                            class="!py-1 !px-3"
                                            @click="discoveredStatusFilter = 'connected'"
                                        >
                                            {{ $t("interfaces.connected_only") }}
                                        </button>
                                    </div>
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
                                {{ discoveredEmptyMessage }}
                            </div>

                            <div
                                v-else
                                class="grid gap-4 min-w-0 grid-cols-1 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 4xl:grid-cols-6"
                            >
                                <div
                                    v-for="iface in sortedDiscoveredInterfaces"
                                    :key="iface.discovery_hash || iface.name"
                                    class="interface-card group transition-all duration-300 min-w-0"
                                    :class="{ 'opacity-70 grayscale-[0.3]': !isDiscoveredConnected(iface) }"
                                >
                                    <div
                                        class="flex flex-col gap-3 sm:flex-row sm:gap-4 sm:items-start relative min-w-0"
                                    >
                                        <!-- Disconnected Overlay -->
                                        <div
                                            v-if="!isDiscoveredConnected(iface)"
                                            class="absolute inset-0 z-10 flex items-center justify-center bg-white/20 dark:bg-zinc-900/20 backdrop-blur-[0.5px] rounded-3xl pointer-events-none"
                                        >
                                            <div
                                                class="bg-red-500/90 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="
                                                        isDiscoveredBlacklisted(iface) ? 'cancel' : 'lan-disconnect'
                                                    "
                                                    class="w-3.5 h-3.5"
                                                />
                                                <span>{{
                                                    isDiscoveredBlacklisted(iface) ? "Blacklisted" : $t("app.disabled")
                                                }}</span>
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

                                        <div
                                            class="flex flex-row sm:flex-col gap-2 shrink-0 self-end sm:self-auto justify-end"
                                        >
                                            <div class="relative">
                                                <button
                                                    type="button"
                                                    class="secondary-chip !p-2 !rounded-xl"
                                                    title="Discovery actions"
                                                    @click="toggleDiscoveryActionsMenu(iface)"
                                                >
                                                    <MaterialDesignIcon icon-name="dots-vertical" class="w-4 h-4" />
                                                </button>
                                                <div
                                                    v-if="openDiscoveryActionKey === discoveryKey(iface)"
                                                    class="absolute right-0 mt-1 z-20 min-w-44 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-lg p-1"
                                                >
                                                    <button
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300"
                                                        :disabled="savingDiscoveryAction"
                                                        @click="addDiscoveredInterfaceToList(iface, 'allow')"
                                                    >
                                                        Allow this announce
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-700 dark:text-red-300"
                                                        :disabled="savingDiscoveryAction"
                                                        @click="addDiscoveredInterfaceToList(iface, 'block')"
                                                    >
                                                        Blacklist this announce
                                                    </button>
                                                </div>
                                            </div>
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
                        <div class="interfaces-subpanel space-y-4">
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
                            <div class="grid gap-4 min-w-0 lg:grid-cols-2">
                                <div class="space-y-2 text-sm text-gray-700 dark:text-gray-300 min-w-0">
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
                                <div class="space-y-3 min-w-0">
                                    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                        <div class="flex flex-col min-w-0 pr-0 sm:pr-4">
                                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                Discover Interfaces (Peer)
                                            </div>
                                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                                Listen for discovery announces and optionally auto-connect to available
                                                interfaces.
                                            </div>
                                        </div>
                                        <Toggle
                                            v-model="discoveryConfig.discover_interfaces"
                                            class="shrink-0 sm:my-auto"
                                        />
                                    </div>
                                    <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 min-w-0">
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
                                                Discovery Whitelist
                                            </div>
                                            <input
                                                v-model="discoveryConfig.interface_discovery_whitelist"
                                                type="text"
                                                placeholder="Names, hosts, ids, or host:port globs"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                                                Discovery Blacklist
                                            </div>
                                            <input
                                                v-model="discoveryConfig.interface_discovery_blacklist"
                                                type="text"
                                                placeholder="Names, hosts, ids, or host:port globs"
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
                interface_discovery_whitelist: "",
                interface_discovery_blacklist: "",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: 0,
                network_identity: "",
            },
            savingDiscovery: false,
            savingDiscoveryAction: false,
            openDiscoveryActionKey: null,
            discoveredInterfaces: [],
            discoveredActive: [],
            discoveredStatusFilter: "all",
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
            const search = this.searchTerm.toLowerCase().trim();
            let list = [...this.discoveredInterfaces];
            if (this.discoveredStatusFilter === "connected") {
                list = list.filter((iface) => this.isDiscoveredConnected(iface));
            }
            if (this.typeFilter !== "all") {
                list = list.filter((iface) => iface.type === this.typeFilter);
            }
            if (search) {
                list = list.filter((iface) => {
                    const haystack = [
                        iface.name,
                        iface.type,
                        iface.reachable_on,
                        iface.port,
                        iface.transport_id,
                        iface.network_id,
                    ]
                        .filter(Boolean)
                        .join(" ")
                        .toLowerCase();
                    return haystack.includes(search);
                });
            }
            return list.sort((a, b) => (b.last_heard || 0) - (a.last_heard || 0));
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
        discoveredEmptyMessage() {
            if (!this.isReticulumRunning) {
                return "LXMF/Reticulum is not running; discovery cannot listen for announces.";
            }
            if (!this.discoveryConfig.discover_interfaces) {
                return "Discovery is disabled. Enable it to start listening for announces.";
            }
            return "Discovery is working, be patient while it waits for announces.";
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
                const response = await window.api.get(`/api/v1/reticulum/interfaces`);
                this.interfaces = response.data.interfaces;

                // also check app info for running state
                const appInfoResponse = await window.api.get(`/api/v1/app/info`);
                this.isReticulumRunning = appInfoResponse.data.app_info.is_reticulum_running;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async updateInterfaceStats() {
            try {
                // fetch interface stats
                const response = await window.api.get(`/api/v1/interface-stats`);

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
                await window.api.post(`/api/v1/reticulum/interfaces/enable`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_enable"));
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async disableInterface(interfaceName) {
            // disable interface
            try {
                await window.api.post(`/api/v1/reticulum/interfaces/disable`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_disable"));
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
            if (!(await DialogUtils.confirm(this.$t("interfaces.delete_confirm")))) {
                return;
            }

            // delete interface
            try {
                await window.api.post(`/api/v1/reticulum/interfaces/delete`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_delete"));
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async exportInterfaces() {
            try {
                // fetch exported interfaces
                const response = await window.api.post("/api/v1/reticulum/interfaces/export");

                // download file to browser
                DownloadUtils.downloadFile("meshchat_interfaces.txt", new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_export_all"));
                console.error(e);
            }
        },
        async exportInterface(interfaceName) {
            try {
                // fetch exported interfaces
                const response = await window.api.post("/api/v1/reticulum/interfaces/export", {
                    selected_interface_names: [interfaceName],
                });

                // download file to browser
                DownloadUtils.downloadFile(`${interfaceName}.txt`, new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_export_single"));
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
                const response = await window.api.get(`/api/v1/reticulum/discovered-interfaces`);
                const incoming = response.data?.interfaces ?? [];
                const active = response.data?.active ?? [];

                const merged = new Map();
                const addOrUpdate = (iface, isNew = false) => {
                    const key = this.discoveryKey(iface);
                    const existing =
                        merged.get(key) || this.discoveredInterfaces.find((i) => this.discoveryKey(i) === key);
                    const lastHeard = iface.last_heard ?? existing?.last_heard ?? Math.floor(Date.now() / 1000);
                    merged.set(key, {
                        ...existing,
                        ...iface,
                        last_heard: lastHeard,
                        __isNew: isNew || existing?.__isNew,
                    });
                };

                this.discoveredInterfaces.forEach((iface) => addOrUpdate(iface, false));
                incoming.forEach((iface) => addOrUpdate(iface, true));

                this.discoveredInterfaces = Array.from(merged.values());
                this.discoveredActive = active;
            } catch (e) {
                console.log(e);
            }
        },
        discoveryKey(iface) {
            return (
                iface.discovery_hash ||
                `${iface.reachable_on || iface.target_host || iface.remote || iface.listen_ip || iface.name || "unknown"}:${
                    iface.port || iface.target_port || iface.listen_port || ""
                }`
            );
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
                const response = await window.api.get(`/api/v1/reticulum/discovery`);
                const discovery = response.data?.discovery ?? {};
                this.discoveryConfig.discover_interfaces = this.parseBool(discovery.discover_interfaces);
                this.discoveryConfig.interface_discovery_sources = discovery.interface_discovery_sources ?? "";
                this.discoveryConfig.interface_discovery_whitelist = discovery.interface_discovery_whitelist ?? "";
                this.discoveryConfig.interface_discovery_blacklist = discovery.interface_discovery_blacklist ?? "";
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
                    interface_discovery_whitelist: this.discoveryConfig.interface_discovery_whitelist || null,
                    interface_discovery_blacklist: this.discoveryConfig.interface_discovery_blacklist || null,
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

                await window.api.patch(`/api/v1/reticulum/discovery`, payload);
                ToastUtils.success(this.$t("interfaces.discovery_settings_saved"));
                await this.loadDiscoveryConfig();
            } catch (e) {
                ToastUtils.error(this.$t("interfaces.failed_save_discovery"));
                console.log(e);
            } finally {
                this.savingDiscovery = false;
            }
        },
        toggleDiscoveryActionsMenu(iface) {
            const key = this.discoveryKey(iface);
            this.openDiscoveryActionKey = this.openDiscoveryActionKey === key ? null : key;
        },
        normalizeDiscoveryPatternInput(value) {
            if (!value) return [];
            return String(value)
                .replace(/\r?\n/g, ",")
                .split(",")
                .map((part) => part.trim())
                .filter(Boolean);
        },
        sanitizeDiscoveryPattern(value) {
            if (value === null || value === undefined) return "";
            return String(value)
                .replace(/[\r\n,]/g, "")
                .trim()
                .slice(0, 128);
        },
        discoveryFilterCandidates(iface) {
            const values = [
                iface.name,
                iface.type,
                iface.reachable_on,
                iface.target_host,
                iface.remote,
                iface.listen_ip,
                iface.port,
                iface.target_port,
                iface.listen_port,
                iface.discovery_hash,
                iface.transport_id,
                iface.network_id,
            ]
                .map((value) => this.sanitizeDiscoveryPattern(value))
                .filter(Boolean);
            const host = this.sanitizeDiscoveryPattern(
                iface.reachable_on || iface.target_host || iface.remote || iface.listen_ip
            );
            const port = this.sanitizeDiscoveryPattern(iface.port || iface.target_port || iface.listen_port);
            if (host && port) {
                values.push(`${host}:${port}`);
            }
            return values.map((value) => value.toLowerCase());
        },
        matchesDiscoveryGlob(pattern, value) {
            const escaped = String(pattern)
                .replace(/[.+^${}()|[\]\\]/g, "\\$&")
                .replace(/\*/g, ".*");
            /* eslint-disable-next-line security/detect-non-literal-regexp -- pattern is escaped above */
            const regex = new RegExp(`^${escaped}$`, "i");
            return regex.test(value);
        },
        isDiscoveredBlacklisted(iface) {
            const blacklist = this.normalizeDiscoveryPatternInput(
                this.discoveryConfig.interface_discovery_blacklist
            ).map((pattern) => this.sanitizeDiscoveryPattern(pattern).toLowerCase());
            if (!blacklist.length) return false;
            const candidates = this.discoveryFilterCandidates(iface);
            return blacklist.some((pattern) =>
                candidates.some((candidate) => this.matchesDiscoveryGlob(pattern, candidate))
            );
        },
        discoveryPatternToken(iface) {
            const host = this.sanitizeDiscoveryPattern(
                iface.reachable_on || iface.target_host || iface.remote || iface.listen_ip
            );
            const port = this.sanitizeDiscoveryPattern(iface.port || iface.target_port || iface.listen_port);
            if (host && port) return `${host}:${port}`;
            return (
                host ||
                this.sanitizeDiscoveryPattern(iface.transport_id) ||
                this.sanitizeDiscoveryPattern(iface.network_id) ||
                this.sanitizeDiscoveryPattern(iface.name)
            );
        },
        async addDiscoveredInterfaceToList(iface, action) {
            if (this.savingDiscoveryAction) return;
            const token = this.discoveryPatternToken(iface);
            this.openDiscoveryActionKey = null;
            if (!token) {
                ToastUtils.error("Unable to identify a filter token from this announce");
                return;
            }

            this.savingDiscoveryAction = true;
            try {
                const whitelist = this.normalizeDiscoveryPatternInput(
                    this.discoveryConfig.interface_discovery_whitelist
                );
                const blacklist = this.normalizeDiscoveryPatternInput(
                    this.discoveryConfig.interface_discovery_blacklist
                );
                const tokenLower = token.toLowerCase();
                const dedupe = (list) =>
                    list.filter(
                        (entry, index, arr) =>
                            arr.findIndex((candidate) => candidate.toLowerCase() === entry.toLowerCase()) === index
                    );

                let nextWhitelist = [...whitelist];
                let nextBlacklist = [...blacklist];
                if (action === "allow") {
                    nextWhitelist.push(token);
                    nextWhitelist = dedupe(nextWhitelist);
                    nextBlacklist = nextBlacklist.filter((entry) => entry.toLowerCase() !== tokenLower);
                } else {
                    nextBlacklist.push(token);
                    nextBlacklist = dedupe(nextBlacklist);
                    nextWhitelist = nextWhitelist.filter((entry) => entry.toLowerCase() !== tokenLower);
                }

                const payload = {
                    interface_discovery_whitelist: nextWhitelist.length ? nextWhitelist.join(",") : null,
                    interface_discovery_blacklist: nextBlacklist.length ? nextBlacklist.join(",") : null,
                };
                await window.api.patch(`/api/v1/reticulum/discovery`, payload);
                this.discoveryConfig.interface_discovery_whitelist = payload.interface_discovery_whitelist || "";
                this.discoveryConfig.interface_discovery_blacklist = payload.interface_discovery_blacklist || "";
                ToastUtils.success(
                    action === "allow"
                        ? `Added ${token} to discovery whitelist`
                        : `Added ${token} to discovery blacklist`
                );
            } catch (e) {
                ToastUtils.error(this.$t("interfaces.failed_save_discovery"));
                console.log(e);
            } finally {
                this.savingDiscoveryAction = false;
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
                const response = await window.api.post("/api/v1/reticulum/reload");
                ToastUtils.success(response.data.message);
                GlobalState.hasPendingInterfaceChanges = false;
                GlobalState.modifiedInterfaceNames.clear();
                await this.loadInterfaces();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("interfaces.failed_reload"));
                console.error(e);
            } finally {
                this.reloadingRns = false;
            }
        },
    },
};
</script>

<style scoped>
.interfaces-section {
    @apply w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8;
}
.interfaces-section--hero {
    @apply border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8;
}
.interfaces-subpanel {
    @apply mt-6 pt-6 border-t border-gray-200/50 dark:border-zinc-800/50 first:mt-0 first:pt-0 first:border-0;
}
</style>
