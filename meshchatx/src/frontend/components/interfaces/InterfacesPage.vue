<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas text-sem-fg">
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4">
            <div class="space-y-0 w-full min-w-0 max-w-6xl xl:max-w-7xl 2xl:max-w-360 mx-auto flex-1">
                <div
                    v-if="showRestartReminder"
                    class="bg-sem-warning text-white border border-amber-500/30 p-4 sm:rounded-xl flex flex-wrap gap-3 items-center mb-3 sm:mb-4"
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
                        class="ml-auto inline-flex items-center gap-2 rounded-full bg-sem-surface px-4 py-1.5 text-sm font-bold text-sem-warning hover:bg-sem-surface transition shadow-xs"
                        @click="relaunch"
                    >
                        <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                        {{ $t("interfaces.restart_now") }}
                    </button>
                </div>

                <div
                    class="interfaces-section interfaces-section--hero flex flex-col lg:flex-row lg:items-center justify-between gap-4"
                >
                    <div class="space-y-3 flex-1 min-w-0">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("interfaces.manage") }}
                        </div>
                        <div class="text-3xl font-black text-sem-fg tracking-tight">
                            {{ $t("interfaces.title") }}
                        </div>
                        <div class="text-sm text-sem-fg-muted leading-relaxed max-w-xl">
                            {{ $t("interfaces.description") }}
                        </div>
                        <div class="flex flex-wrap gap-2 pt-2">
                            <RouterLink
                                :to="{ name: 'interfaces.add' }"
                                class="primary-chip px-4 py-2 text-sm min-h-[44px] sm:min-h-0 items-center justify-center hidden sm:inline-flex"
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
                                class="secondary-chip text-sm transition-shadow"
                                :class="
                                    showRestartReminder
                                        ? 'ring-2 ring-sem-warning shadow-lg shadow-amber-500/40 animate-pulse motion-reduce:animate-none'
                                        : ''
                                "
                                :disabled="reloadingRns"
                                @click="reloadRns"
                            >
                                <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                                <span>{{ reloadingRns ? $t("app.reloading_rns") : "Restart RNS" }}</span>
                            </button>
                        </div>
                    </div>

                    <div class="w-full md:w-96 shrink-0 space-y-4">
                        <SearchInput v-model="searchTerm" :placeholder="$t('interfaces.search_placeholder')" />
                        <div>
                            <select
                                v-model="typeFilter"
                                class="w-full px-4 py-2.5 bg-sem-surface border border-sem-border rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-sem-info/50 text-sem-fg"
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
                                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">Configured</div>
                                    <div class="text-xl font-semibold text-sem-fg">
                                        Interfaces
                                        <span
                                            v-if="filteredInterfaces.length > 0"
                                            class="ml-2 text-sm font-medium text-sem-fg-muted"
                                            >({{ filteredInterfaces.length }})</span
                                        >
                                    </div>
                                </div>
                                <div class="flex gap-2 flex-wrap">
                                    <button
                                        type="button"
                                        :class="filterChipClass(statusFilter === 'all')"
                                        class="py-1! px-3!"
                                        @click="setStatusFilter('all')"
                                    >
                                        {{ $t("interfaces.all") }}
                                    </button>
                                    <button
                                        type="button"
                                        :class="filterChipClass(statusFilter === 'enabled')"
                                        class="py-1! px-3!"
                                        @click="setStatusFilter('enabled')"
                                    >
                                        {{ $t("app.enabled") }}
                                    </button>
                                    <button
                                        type="button"
                                        :class="filterChipClass(statusFilter === 'disabled')"
                                        class="py-1! px-3!"
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
                                    @share="shareInterface(iface)"
                                    @delete="deleteInterface(iface._name)"
                                    @reload="restartInterface(iface._name)"
                                />
                            </div>
                            <div
                                v-else
                                class="text-center py-10 px-4 text-gray-500 dark:text-sem-fg-secondary border border-dashed border-sem-border rounded-xl"
                            >
                                <MaterialDesignIcon icon-name="lan-disconnect" class="w-10 h-10 mx-auto mb-3" />
                                <div class="text-lg font-semibold">{{ $t("interfaces.no_interfaces_found") }}</div>
                                <div class="text-sm">{{ $t("interfaces.no_interfaces_description") }}</div>
                            </div>
                        </div>

                        <div class="interfaces-subpanel space-y-3">
                            <div class="flex flex-col gap-3 min-w-0 lg:flex-row lg:items-start lg:justify-between">
                                <div class="min-w-0 flex-1">
                                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                                        Discovered Interfaces
                                    </div>
                                    <div class="text-xl font-semibold text-sem-fg">
                                        Recently Heard Announces
                                        <span
                                            v-if="sortedDiscoveredInterfaces.length > 0"
                                            class="ml-2 text-sm font-medium text-sem-fg-muted"
                                            >({{ sortedDiscoveredInterfaces.length }})</span
                                        >
                                    </div>
                                    <div class="text-sm text-sem-fg-muted">
                                        Discovery runs continually. Heard announces stay listed. Connected entries show
                                        a green pill. Disconnected entries are dimmed with a red label.
                                    </div>
                                </div>
                                <div class="flex flex-wrap gap-2 items-center shrink-0 min-w-0">
                                    <div class="flex gap-1.5 mr-2">
                                        <button
                                            type="button"
                                            :class="filterChipClass(discoveredStatusFilter === 'all')"
                                            class="py-1! px-3!"
                                            @click="discoveredStatusFilter = 'all'"
                                        >
                                            {{ $t("interfaces.all") }}
                                        </button>
                                        <button
                                            type="button"
                                            :class="filterChipClass(discoveredStatusFilter === 'connected')"
                                            class="py-1! px-3!"
                                            @click="discoveredStatusFilter = 'connected'"
                                        >
                                            {{ $t("interfaces.connected_only") }}
                                        </button>
                                    </div>
                                    <button
                                        v-if="interfacesWithLocation.length > 0"
                                        type="button"
                                        class="secondary-chip text-xs bg-sem-warning/15 hover:bg-sem-warning/15 text-sem-accent border-blue-500/30"
                                        @click="mapAllDiscovered"
                                    >
                                        <MaterialDesignIcon icon-name="map-marker-multiple" class="w-4 h-4" />
                                        Map All ({{ interfacesWithLocation.length }})
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip text-xs"
                                        :disabled="exportingDiscoveredInterfaces"
                                        @click="exportDiscoveredInterfaces"
                                    >
                                        <MaterialDesignIcon icon-name="export" class="w-4 h-4" />
                                        Export
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip text-xs"
                                        :disabled="importingDiscoveredInterfaces"
                                        @click="onImportDiscoveredClick"
                                    >
                                        <MaterialDesignIcon icon-name="import" class="w-4 h-4" />
                                        Import
                                    </button>
                                    <input
                                        ref="discovered-import-input"
                                        type="file"
                                        accept=".zip,application/zip"
                                        class="hidden"
                                        @change="onDiscoveredImportFile"
                                    />
                                    <button
                                        type="button"
                                        class="secondary-chip text-xs"
                                        @click="refreshDiscoveredInterfacesList"
                                    >
                                        <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                                        Refresh
                                    </button>
                                </div>
                            </div>

                            <div
                                v-if="sortedDiscoveredInterfaces.length === 0"
                                class="text-sm text-gray-500 dark:text-sem-fg-secondary"
                            >
                                {{ discoveredEmptyMessage }}
                            </div>

                            <div
                                v-else
                                class="grid gap-4 min-w-0 grid-cols-1 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 4xl:grid-cols-6"
                            >
                                <div
                                    v-for="iface in pagedDiscoveredInterfaces"
                                    :key="iface.discovery_hash || iface.name"
                                    class="interface-card group transition-all duration-300 min-w-0"
                                    :class="{
                                        'opacity-85 md:opacity-70 md:grayscale-[0.3]': !isDiscoveredConnected(iface),
                                    }"
                                >
                                    <div
                                        class="flex flex-col gap-3 sm:flex-row sm:gap-4 sm:items-start relative min-w-0 pt-11 sm:pt-0"
                                    >
                                        <!-- Disconnected Overlay -->
                                        <div
                                            v-if="!isDiscoveredConnected(iface)"
                                            class="absolute inset-0 z-10 flex items-center justify-center bg-white/25 dark:bg-sem-surface md:backdrop-blur-[0.5px] rounded-3xl pointer-events-none"
                                        >
                                            <div
                                                class="bg-sem-action-danger/90 text-sem-action-danger-text px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"
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

                                        <div class="flex gap-3 sm:gap-4 min-w-0 flex-1">
                                            <div class="interface-card__icon shrink-0">
                                                <MaterialDesignIcon
                                                    :icon-name="getDiscoveryIcon(iface)"
                                                    class="w-6 h-6"
                                                />
                                            </div>

                                            <div class="flex-1 min-w-0 space-y-2">
                                                <div class="flex items-center gap-2 flex-nowrap min-w-0">
                                                    <div
                                                        class="text-base sm:text-lg font-semibold text-sem-fg truncate min-w-0"
                                                    >
                                                        {{ iface.name }}
                                                    </div>
                                                    <span class="type-chip shrink-0">{{ iface.type }}</span>
                                                </div>

                                                <div class="flex items-center gap-2 flex-wrap">
                                                    <span
                                                        v-if="iface.value"
                                                        class="text-[10px] font-bold text-sem-accent"
                                                    >
                                                        Stamps: {{ iface.value }}
                                                    </span>
                                                    <span
                                                        v-if="isDiscoveredConnected(iface)"
                                                        class="inline-flex items-center rounded-full bg-sem-success/15 text-sem-success px-2 py-0.5 text-[10px] font-semibold dark:bg-sem-success/15 text-sem-success shrink-0"
                                                    >
                                                        Connected
                                                    </span>
                                                    <span
                                                        v-if="iface.is_blacklisted"
                                                        class="inline-flex items-center rounded-full bg-sem-danger/15 text-sem-danger px-2 py-0.5 text-[10px] font-semibold dark:bg-sem-danger/15 text-sem-danger shrink-0"
                                                    >
                                                        Blocked
                                                    </span>
                                                    <span
                                                        v-else-if="iface.is_allowed === false"
                                                        class="inline-flex items-center rounded-full bg-sem-warning/15 text-sem-warning px-2 py-0.5 text-[10px] font-semibold dark:bg-sem-warning/15 dark:text-sem-warning shrink-0"
                                                    >
                                                        Not allowed
                                                    </span>
                                                </div>

                                                <div class="flex flex-wrap gap-1.5 text-[10px] sm:text-xs">
                                                    <span class="stat-chip bg-sem-surface-muted/50"
                                                        >Hops: {{ iface.hops }}</span
                                                    >
                                                    <span class="stat-chip capitalize bg-sem-surface-muted/50">{{
                                                        iface.status
                                                    }}</span>
                                                    <span
                                                        v-if="iface.impl_name"
                                                        class="stat-chip bg-sem-surface-muted/50"
                                                        :title="$t('interfaces.discovered_impl_hint')"
                                                    >
                                                        {{ iface.impl_name
                                                        }}<template v-if="iface.version"> {{ iface.version }}</template>
                                                    </span>
                                                    <span
                                                        v-if="iface.last_heard"
                                                        class="stat-chip bg-sem-surface-muted/50"
                                                    >
                                                        Heard: {{ formatLastHeard(iface.last_heard) }}
                                                    </span>
                                                    <template v-if="discoveredBytes(iface)">
                                                        <span class="stat-chip bg-sem-surface-muted/50">
                                                            {{ $t("interface.tx") }}
                                                            {{ discoveredBytes(iface).tx }}
                                                        </span>
                                                        <span class="stat-chip bg-sem-surface-muted/50">
                                                            {{ $t("interface.rx") }}
                                                            {{ discoveredBytes(iface).rx }}
                                                        </span>
                                                    </template>
                                                </div>

                                                <div class="grid gap-1.5 text-[10px] sm:text-[11px] pt-1 min-w-0">
                                                    <div
                                                        v-if="iface.reachable_on"
                                                        class="flex items-center gap-2 text-sem-fg-muted hover:text-sem-info cursor-pointer transition-colors min-w-0"
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
                                                        class="flex items-center gap-2 text-sem-fg-muted hover:text-sem-info cursor-pointer transition-colors min-w-0"
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
                                                        class="flex items-center gap-2 text-sem-fg-muted hover:text-sem-info cursor-pointer transition-colors min-w-0"
                                                        @click="copyToClipboard(iface.network_id, 'Network ID')"
                                                    >
                                                        <MaterialDesignIcon
                                                            icon-name="lan"
                                                            class="w-3.5 h-3.5 shrink-0"
                                                        />
                                                        <span class="truncate font-mono"
                                                            >Network ID: {{ iface.network_id }}</span
                                                        >
                                                    </div>

                                                    <div
                                                        v-if="discoveredNetworkName(iface)"
                                                        class="flex items-center gap-2 text-sem-warning hover:text-sem-warning cursor-pointer transition-colors min-w-0"
                                                        :title="$t('interfaces.discovered_copy_network_name')"
                                                        data-testid="discovered-network-name"
                                                        @click="
                                                            copyToClipboard(
                                                                discoveredNetworkName(iface),
                                                                $t('interfaces.discovered_network_name')
                                                            )
                                                        "
                                                    >
                                                        <MaterialDesignIcon
                                                            icon-name="shield-key"
                                                            class="w-3.5 h-3.5 shrink-0"
                                                        />
                                                        <span class="truncate font-mono"
                                                            >{{ $t("interfaces.discovered_network_name") }}:
                                                            {{ discoveredNetworkName(iface) }}</span
                                                        >
                                                    </div>

                                                    <div
                                                        v-if="discoveredPassphrase(iface)"
                                                        class="flex items-center gap-2 text-sem-warning hover:text-sem-warning cursor-pointer transition-colors min-w-0"
                                                        :title="$t('interfaces.discovered_copy_passphrase')"
                                                        data-testid="discovered-passphrase"
                                                        @click="
                                                            copyToClipboard(
                                                                discoveredPassphrase(iface),
                                                                $t('interfaces.discovered_passphrase')
                                                            )
                                                        "
                                                    >
                                                        <MaterialDesignIcon
                                                            icon-name="shield-lock"
                                                            class="w-3.5 h-3.5 shrink-0"
                                                        />
                                                        <span class="truncate font-mono"
                                                            >{{ $t("interfaces.discovered_passphrase") }}:
                                                            {{ maskPassphrase(discoveredPassphrase(iface)) }}</span
                                                        >
                                                    </div>

                                                    <div
                                                        v-if="iface.latitude != null && iface.longitude != null"
                                                        class="flex items-center gap-2 text-sem-fg-muted hover:text-sem-info cursor-pointer transition-colors min-w-0"
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
                                                </div>
                                            </div>
                                        </div>

                                        <div
                                            class="absolute top-0 right-0 z-20 flex flex-row gap-1 sm:static sm:z-auto sm:ml-auto sm:flex-col sm:gap-2 sm:shrink-0 sm:self-auto sm:justify-end"
                                        >
                                            <div v-click-outside="closeDiscoveryActionsMenu" class="relative">
                                                <button
                                                    type="button"
                                                    class="secondary-chip p-2! rounded-xl!"
                                                    title="Discovery actions"
                                                    @click.stop="toggleDiscoveryActionsMenu(iface)"
                                                >
                                                    <MaterialDesignIcon icon-name="dots-vertical" class="w-4 h-4" />
                                                </button>
                                                <div
                                                    v-if="openDiscoveryActionKey === discoveryKey(iface)"
                                                    class="absolute right-0 mt-1 z-20 min-w-44 rounded-xl border border-sem-border bg-sem-surface shadow-lg p-1"
                                                >
                                                    <button
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-sem-info/15 dark:hover:bg-sem-info/15 text-sem-info"
                                                        data-testid="use-discovered-interface"
                                                        @click="useDiscoveredInterface(iface)"
                                                    >
                                                        {{ $t("interfaces.discovered_use_this") }}
                                                    </button>
                                                    <button
                                                        v-if="iface.config_entry"
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-sem-surface-muted text-sem-fg"
                                                        data-testid="copy-discovered-config"
                                                        @click="copyDiscoveredConfigEntry(iface)"
                                                    >
                                                        {{ $t("interfaces.discovered_copy_config") }}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-sem-success/15 dark:hover:bg-sem-success/15 text-sem-success"
                                                        :disabled="savingDiscoveryAction"
                                                        @click="addDiscoveredInterfaceToList(iface, 'allow')"
                                                    >
                                                        Allow this announce
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-sem-danger/15 dark:hover:bg-sem-danger/15 text-sem-danger"
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
                                                class="secondary-chip p-2! rounded-xl!"
                                                :title="$t('map.title')"
                                                @click="goToMap(iface)"
                                            >
                                                <MaterialDesignIcon icon-name="map" class="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="sortedDiscoveredInterfaces.length > discoveredPageSize || discoveredPage > 1"
                                class="flex flex-wrap items-center justify-between gap-3 pt-1"
                            >
                                <div class="text-xs text-sem-fg-muted">
                                    {{ discoveredRangeStart }}-{{ discoveredRangeEnd }} of
                                    {{ sortedDiscoveredInterfaces.length }}
                                </div>
                                <div class="flex items-center gap-2">
                                    <select
                                        v-model.number="discoveredPageSize"
                                        class="input-field w-auto! py-1! text-xs"
                                        aria-label="Items per page"
                                    >
                                        <option :value="24">24</option>
                                        <option :value="48">48</option>
                                        <option :value="96">96</option>
                                        <option :value="192">192</option>
                                    </select>
                                    <button
                                        type="button"
                                        class="secondary-chip text-xs py-1! px-3!"
                                        :disabled="discoveredPage <= 1"
                                        @click="discoveredPage -= 1"
                                    >
                                        <MaterialDesignIcon icon-name="chevron-left" class="w-4 h-4" />
                                        {{ $t("interfaces.previous") }}
                                    </button>
                                    <span class="text-xs text-sem-fg-muted">
                                        {{ discoveredPage }} / {{ discoveredPageCount }}
                                    </span>
                                    <button
                                        type="button"
                                        class="secondary-chip text-xs py-1! px-3!"
                                        :disabled="discoveredPage >= discoveredPageCount"
                                        @click="discoveredPage += 1"
                                    >
                                        {{ $t("interfaces.next") }}
                                        <MaterialDesignIcon icon-name="chevron-right" class="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-else class="space-y-4">
                        <div class="interfaces-subpanel space-y-4">
                            <div class="flex flex-wrap gap-3 items-center">
                                <div class="flex-1">
                                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">Discovery</div>
                                    <div class="text-xl font-semibold text-sem-fg">Interface Discovery</div>
                                    <div class="text-sm text-sem-fg-muted">
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
                                <div class="space-y-2 text-sm text-sem-fg min-w-0">
                                    <div class="font-semibold text-sem-fg">Publish (Server)</div>
                                    <div>
                                        Enable discovery while adding or editing an interface to broadcast reachable
                                        details. Reticulum will sign and stamp announces automatically.
                                    </div>
                                    <div class="text-xs text-sem-fg-muted">
                                        Requires LXMF in the Python environment. Transport is optional for publishing,
                                        but usually recommended so peers can connect back.
                                    </div>
                                </div>
                                <div class="space-y-3 min-w-0">
                                    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                        <div class="flex flex-col min-w-0 pr-0 sm:pr-4">
                                            <div class="text-sm font-semibold text-sem-fg">
                                                Discover Interfaces (Peer)
                                            </div>
                                            <div class="text-xs text-sem-fg-muted">
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
                                            <div class="text-xs font-semibold text-sem-fg">Allowed Sources</div>
                                            <input
                                                v-model="discoveryConfig.interface_discovery_sources"
                                                type="text"
                                                placeholder="Comma separated identity hashes"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Discovery Whitelist</div>
                                            <input
                                                v-model="discoveryConfig.interface_discovery_whitelist"
                                                type="text"
                                                placeholder="Names, hosts, ids, or host:port globs"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Discovery Blacklist</div>
                                            <input
                                                v-model="discoveryConfig.interface_discovery_blacklist"
                                                type="text"
                                                placeholder="Names, hosts, ids, or host:port globs"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Required Stamp Value</div>
                                            <input
                                                v-model.number="discoveryConfig.required_discovery_value"
                                                type="number"
                                                min="0"
                                                class="input-field"
                                            />
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Max Stored Interfaces</div>
                                            <input
                                                v-model.number="discoveryConfig.discovered_interfaces_max_return"
                                                type="number"
                                                min="1"
                                                max="50000"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">
                                                Cap on stored and listed discovered interfaces, default 500.
                                            </div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">
                                                Mark Unknown After (Days)
                                            </div>
                                            <input
                                                v-model.number="discoveryConfig.interface_discovery_unknown_after_days"
                                                type="number"
                                                min="0"
                                                step="0.5"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">Default 1 day.</div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Mark Stale After (Days)</div>
                                            <input
                                                v-model.number="discoveryConfig.interface_discovery_stale_after_days"
                                                type="number"
                                                min="0"
                                                step="0.5"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">Default 3 days.</div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Delete After (Days)</div>
                                            <input
                                                v-model.number="discoveryConfig.interface_discovery_remove_after_days"
                                                type="number"
                                                min="0"
                                                step="0.5"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">
                                                Discovered interfaces older than this are deleted, default 7 days.
                                            </div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Auto-connect Slots</div>
                                            <input
                                                v-model.number="discoveryConfig.autoconnect_discovered_interfaces"
                                                type="number"
                                                min="0"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">0 disables auto-connect.</div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">
                                                {{ $t("interfaces.default_gravity_label") }}
                                            </div>
                                            <input
                                                v-model.number="discoveryConfig.default_gravity"
                                                type="number"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">
                                                {{ $t("interfaces.default_gravity_hint") }}
                                            </div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">
                                                {{ $t("interfaces.autoconnect_interface_mode_label") }}
                                            </div>
                                            <select
                                                v-model="discoveryConfig.autoconnect_interface_mode"
                                                class="input-field"
                                            >
                                                <option value="">
                                                    {{ $t("interfaces.mode_default_full") }}
                                                </option>
                                                <option value="full">
                                                    {{ $t("interfaces.mode_full") }}
                                                </option>
                                                <option value="gateway">
                                                    {{ $t("interfaces.mode_gateway") }}
                                                </option>
                                                <option value="access_point">
                                                    {{ $t("interfaces.mode_access_point") }}
                                                </option>
                                                <option value="roaming">
                                                    {{ $t("interfaces.mode_roaming") }}
                                                </option>
                                                <option value="boundary">
                                                    {{ $t("interfaces.mode_boundary") }}
                                                </option>
                                                <option value="internal">
                                                    {{ $t("interfaces.mode_internal") }}
                                                </option>
                                            </select>
                                            <div class="text-xs text-sem-fg-muted">
                                                {{ $t("interfaces.autoconnect_interface_mode_hint") }}
                                            </div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">
                                                {{ $t("interfaces.autoconnect_interface_gravity_label") }}
                                            </div>
                                            <input
                                                v-model.number="discoveryConfig.autoconnect_interface_gravity"
                                                type="number"
                                                class="input-field"
                                            />
                                            <div class="text-xs text-sem-fg-muted">
                                                {{ $t("interfaces.autoconnect_interface_gravity_hint") }}
                                            </div>
                                        </div>
                                        <div class="sm:col-span-2">
                                            <div
                                                class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                                            >
                                                <div class="min-w-0 pr-0 sm:pr-4">
                                                    <div class="text-sm font-semibold text-sem-fg">
                                                        {{ $t("interfaces.autoconnect_announces_to_internal_label") }}
                                                    </div>
                                                    <div class="text-xs text-sem-fg-muted">
                                                        {{ $t("interfaces.autoconnect_announces_to_internal_hint") }}
                                                    </div>
                                                </div>
                                                <Toggle
                                                    v-model="discoveryConfig.autoconnect_announces_to_internal"
                                                    class="shrink-0 sm:my-auto"
                                                />
                                            </div>
                                        </div>
                                        <div class="sm:col-span-2">
                                            <div
                                                class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                                            >
                                                <div class="min-w-0 pr-0 sm:pr-4">
                                                    <div class="text-sm font-semibold text-sem-fg">
                                                        {{ $t("interfaces.autoconnect_unverified_label") }}
                                                    </div>
                                                    <div class="text-xs text-sem-fg-muted">
                                                        {{ $t("interfaces.autoconnect_unverified_hint") }}
                                                    </div>
                                                </div>
                                                <Toggle
                                                    v-model="discoveryConfig.autoconnect_unverified_implementations"
                                                    class="shrink-0 sm:my-auto"
                                                />
                                            </div>
                                        </div>
                                        <div class="sm:col-span-2">
                                            <div
                                                class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                                            >
                                                <div class="min-w-0 pr-0 sm:pr-4">
                                                    <div class="text-sm font-semibold text-sem-fg">
                                                        {{ $t("interfaces.discovery_default_bootstrap_only") }}
                                                    </div>
                                                    <div class="text-xs text-sem-fg-muted">
                                                        <BundledDocsHint paragraph-class="text-xs text-sem-fg-muted" />
                                                    </div>
                                                </div>
                                                <Toggle
                                                    v-model="discoveryConfig.default_bootstrap_only"
                                                    class="shrink-0 sm:my-auto"
                                                />
                                            </div>
                                        </div>
                                        <div>
                                            <div class="text-xs font-semibold text-sem-fg">Network Identity Path</div>
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

        <RouterLink
            :to="{ name: 'interfaces.add' }"
            class="sm:hidden fixed bottom-5 right-4 z-60 flex h-14 w-14 items-center justify-center rounded-full bg-sem-action-primary text-sem-action-primary-text shadow-lg ring-1 ring-sem-info transition active:scale-95"
            :title="$t('interfaces.add_interface')"
        >
            <MaterialDesignIcon icon-name="plus" class="w-7 h-7" />
        </RouterLink>

        <ImportInterfacesModal ref="import-interfaces-modal" @dismissed="onImportInterfacesModalDismissed" />
    </div>
</template>

<script>
import { useNetworkStore } from "../../js/stores/networkStore";
import { useInterfaceChangesStore } from "../../js/stores/interfaceChangesStore.js";
import DialogUtils from "../../js/DialogUtils";
import ElectronUtils from "../../js/ElectronUtils";
import Interface from "./Interface.vue";
import { getCurrentInstance } from "vue";
import Utils from "../../js/Utils";
import ImportInterfacesModal from "./ImportInterfacesModal.vue";
import DownloadUtils from "../../js/DownloadUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SearchInput from "../SearchInput.vue";
import ToastUtils from "../../js/ToastUtils";
import { copyTextToClipboard } from "../../js/clipboardUtils.js";
import Toggle from "../forms/Toggle.vue";
import BundledDocsHint from "./BundledDocsHint.vue";
import GlobalEmitter from "../../js/GlobalEmitter";
import { apiPath, EMITTER_EVENTS, STORAGE_KEYS } from "../../js/constants";
import { useInterfaceListFilters } from "../../js/interfaces/useInterfaceListFilters.js";
import { BATTERY_SAVER_CHANGED_EVENT, loadBatterySaverPrefs } from "../../js/settings/batterySaverPrefs.js";

// Default bound for the discovered-interfaces accumulation across discovery
// polls when the backend cap setting is unavailable.
const DEFAULT_DISCOVERED_INTERFACES_CAP = 500;

export default {
    name: "InterfacesPage",
    components: {
        Toggle,
        ImportInterfacesModal,
        Interface,
        MaterialDesignIcon,
        SearchInput,
        BundledDocsHint,
    },
    setup() {
        const inst = getCurrentInstance();
        return {
            ...useInterfaceListFilters({
                getInterfaces: () => inst?.proxy.interfacesWithStats ?? [],
            }),
        };
    },
    data() {
        return {
            interfaces: {},
            interfaceStats: {},
            reloadInterval: null,
            reloadingRns: false,
            isReticulumRunning: true,
            discoveryConfig: {
                discover_interfaces: false,
                interface_discovery_sources: "",
                interface_discovery_whitelist: "",
                interface_discovery_blacklist: "",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: null,
                default_gravity: null,
                autoconnect_interface_mode: "",
                autoconnect_interface_gravity: null,
                autoconnect_announces_to_internal: false,
                autoconnect_unverified_implementations: false,
                default_bootstrap_only: false,
                discovered_interfaces_max_return: null,
                interface_discovery_unknown_after_days: null,
                interface_discovery_stale_after_days: null,
                interface_discovery_remove_after_days: null,
                network_identity: "",
            },
            savingDiscovery: false,
            savingDiscoveryAction: false,
            openDiscoveryActionKey: null,
            discoveredInterfaces: [],
            discoveredActive: [],
            exportingDiscoveredInterfaces: false,
            importingDiscoveredInterfaces: false,
            discoveredStatusFilter: "all",
            discoveredPage: 1,
            discoveredPageSize: 48,
            discoveryInterval: null,
            activeTab: "overview",
        };
    },
    computed: {
        hasPendingInterfaceChanges() {
            return useInterfaceChangesStore().hasPendingInterfaceChanges;
        },
        modifiedInterfaceNames() {
            return useInterfaceChangesStore().modifiedInterfaceNames;
        },
        isElectron() {
            return ElectronUtils.isElectron();
        },
        discoveredInterfacesCap() {
            const value = Number(this.discoveryConfig?.discovered_interfaces_max_return);
            if (Number.isFinite(value) && value > 0) {
                return Math.min(value, 50_000);
            }
            return DEFAULT_DISCOVERED_INTERFACES_CAP;
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
        pagedDiscoveredInterfaces() {
            const start = (this.discoveredPage - 1) * this.discoveredPageSize;
            return this.sortedDiscoveredInterfaces.slice(start, start + this.discoveredPageSize);
        },
        discoveredPageCount() {
            return Math.max(1, Math.ceil(this.sortedDiscoveredInterfaces.length / this.discoveredPageSize));
        },
        discoveredRangeStart() {
            if (this.sortedDiscoveredInterfaces.length === 0) return 0;
            return (this.discoveredPage - 1) * this.discoveredPageSize + 1;
        },
        discoveredRangeEnd() {
            return Math.min(this.discoveredPage * this.discoveredPageSize, this.sortedDiscoveredInterfaces.length);
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
                    set.add(String(a.transport_id).toLowerCase());
                }
            });
            return set;
        },
        discoveredEmptyMessage() {
            if (!this.isReticulumRunning) {
                return "LXMF/Reticulum is not running. Discovery cannot listen for announces.";
            }
            if (!this.discoveryConfig.discover_interfaces) {
                return "Discovery is disabled. Enable it to start listening for announces.";
            }
            return "Discovery is working, be patient while it waits for announces.";
        },
        discoveryAutoconnectMetadataPresent() {
            const fromActive = (this.discoveredActive || []).some(
                (a) => a.autoconnect_source != null && a.autoconnect_source !== undefined
            );
            const fromStats = (this.activeInterfaceStats || []).some(
                (s) => s.autoconnect_source != null && s.autoconnect_source !== undefined
            );
            return fromActive || fromStats;
        },
    },
    watch: {
        discoveredStatusFilter(value) {
            this.discoveredPage = 1;
            try {
                localStorage.setItem(STORAGE_KEYS.INTERFACES_DISCOVERED_STATUS_FILTER, value);
            } catch {
                /* ignore */
            }
        },
        searchTerm() {
            this.discoveredPage = 1;
        },
        typeFilter() {
            this.discoveredPage = 1;
        },
        discoveredPageCount(count) {
            if (this.discoveredPage > count) {
                this.discoveredPage = count;
            }
        },
        sortedDiscoveredInterfaces() {
            if (this.discoveredPage > this.discoveredPageCount) {
                this.discoveredPage = this.discoveredPageCount;
            }
        },
    },
    beforeUnmount() {
        clearInterval(this.reloadInterval);
        clearInterval(this.discoveryInterval);
        if (this._batterySaverPrefsHandler) {
            GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, this._batterySaverPrefsHandler);
        }
        GlobalEmitter.off(EMITTER_EVENTS.IDENTITY_SWITCHED, this.onIdentitySwitched);
        GlobalEmitter.off(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, this.onWebsocketReconnected);
        if (typeof this._liveTransportReadyWatch === "function") {
            this._liveTransportReadyWatch();
            this._liveTransportReadyWatch = null;
        }
    },
    mounted() {
        try {
            const df = localStorage.getItem(STORAGE_KEYS.INTERFACES_DISCOVERED_STATUS_FILTER);
            if (df === "all" || df === "connected") {
                this.discoveredStatusFilter = df;
            }
        } catch {
            /* ignore */
        }
        this.loadInterfaces();
        this.updateInterfaceStats();
        this.loadDiscoveryConfig();
        this.loadDiscoveredInterfaces();

        this._batterySaverPrefsHandler = () => {
            this.startInterfacePollIntervals();
        };
        GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, this._batterySaverPrefsHandler);
        GlobalEmitter.on(EMITTER_EVENTS.IDENTITY_SWITCHED, this.onIdentitySwitched);
        GlobalEmitter.on(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, this.onWebsocketReconnected);
        this._liveTransportReadyWatch = this.$watch(
            () => useNetworkStore().liveTransportReady,
            () => {
                this.startInterfacePollIntervals();
            }
        );
        this.startInterfacePollIntervals();
    },
    methods: {
        onIdentitySwitched() {
            this.loadInterfaces();
            this.updateInterfaceStats();
            this.loadDiscoveryConfig();
            this.loadDiscoveredInterfaces();
        },
        onWebsocketReconnected() {
            this.loadInterfaces();
            this.updateInterfaceStats();
            this.loadDiscoveryConfig();
            this.loadDiscoveredInterfaces();
        },
        startInterfacePollIntervals() {
            clearInterval(this.reloadInterval);
            clearInterval(this.discoveryInterval);
            this.reloadInterval = null;
            this.discoveryInterval = null;
            const prefs = loadBatterySaverPrefs();
            const liveReady = useNetworkStore().liveTransportReady === true;
            let statsMs =
                prefs.enabled && prefs.reduceInterfacesDiscovery ? prefs.interfacesStatsPollSeconds * 1000 : 1000;
            let discoveryMs =
                prefs.enabled && prefs.reduceInterfacesDiscovery ? prefs.interfacesDiscoveryPollSeconds * 1000 : 5000;
            if (liveReady) {
                statsMs = Math.max(statsMs, 15000);
                discoveryMs = Math.max(discoveryMs, 30000);
            }
            this.reloadInterval = setInterval(() => {
                this.updateInterfaceStats();
            }, statsMs);
            this.discoveryInterval = setInterval(() => {
                this.loadDiscoveredInterfaces();
            }, discoveryMs);
        },
        relaunch() {
            ElectronUtils.relaunch();
        },
        trackInterfaceChange(interfaceName = null) {
            useInterfaceChangesStore().hasPendingInterfaceChanges = true;
            if (interfaceName) {
                useInterfaceChangesStore().modifiedInterfaceNames.add(interfaceName);
            }
        },
        untrackInterfaceChange(interfaceName) {
            // A change that was applied live via RNS interface management
            // no longer needs a full stack restart.
            const store = useInterfaceChangesStore();
            if (interfaceName) {
                store.modifiedInterfaceNames.delete(interfaceName);
            }
            if (store.modifiedInterfaceNames.size === 0) {
                store.hasPendingInterfaceChanges = false;
            }
        },
        isInterfaceEnabled: function (iface) {
            return Utils.isInterfaceEnabled(iface);
        },
        async loadInterfaces() {
            try {
                const response = await window.api.get(apiPath("/reticulum/interfaces"));
                this.interfaces = response.data.interfaces;

                // also check app info for running state
                const appInfoResponse = await window.api.get(apiPath("/app/info"));
                this.isReticulumRunning = appInfoResponse.data.app_info.is_reticulum_running;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async updateInterfaceStats() {
            try {
                // fetch interface stats
                const response = await window.api.get(apiPath("/interface-stats"));

                // Replace the map so deleted/renamed interfaces do not keep
                // stale Connected indicators for discovery peers.
                const nextStats = {};
                const interfaces = response.data.interface_stats?.interfaces ?? [];
                for (const iface of interfaces) {
                    const key = iface.interface_name ?? iface.short_name;
                    if (key) {
                        nextStats[key] = iface;
                    }
                }
                this.interfaceStats = nextStats;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async enableInterface(interfaceName) {
            // enable interface
            try {
                const response = await window.api.post(apiPath("/reticulum/interfaces/enable"), {
                    name: interfaceName,
                });
                if (response?.data?.applied_live === true) {
                    this.untrackInterfaceChange(interfaceName);
                } else {
                    this.trackInterfaceChange(interfaceName);
                }
            } catch (e) {
                DialogUtils.alert(
                    e?.response?.data?.error || e?.response?.data?.message || this.$t("interfaces.failed_enable")
                );
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async disableInterface(interfaceName) {
            // disable interface
            try {
                const response = await window.api.post(apiPath("/reticulum/interfaces/disable"), {
                    name: interfaceName,
                });
                if (response?.data?.applied_live === true) {
                    this.untrackInterfaceChange(interfaceName);
                } else {
                    this.trackInterfaceChange(interfaceName);
                }
            } catch (e) {
                DialogUtils.alert(
                    e?.response?.data?.error || e?.response?.data?.message || this.$t("interfaces.failed_disable")
                );
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async restartInterface(interfaceName) {
            // live reload via RNS 1.5.5 interface management
            try {
                const response = await window.api.post(apiPath("/reticulum/interfaces/reload"), {
                    name: interfaceName,
                });
                ToastUtils.success(response?.data?.message || this.$t("interfaces.reloaded"));
                this.untrackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert(
                    e?.response?.data?.error ||
                        e?.response?.data?.message ||
                        this.$t("interfaces.failed_reload_interface")
                );
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
                const response = await window.api.post(apiPath("/reticulum/interfaces/delete"), {
                    name: interfaceName,
                });
                if (response?.data?.applied_live === true) {
                    this.untrackInterfaceChange(interfaceName);
                } else {
                    this.trackInterfaceChange(interfaceName);
                }
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
                const response = await window.api.post(apiPath("/reticulum/interfaces/export"));

                // download file to browser
                await DownloadUtils.downloadFile("meshchat_interfaces.txt", new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_export_all"));
                console.error(e);
            }
        },
        async exportInterface(interfaceName) {
            try {
                // fetch exported interfaces
                const response = await window.api.post(apiPath("/reticulum/interfaces/export"), {
                    selected_interface_names: [interfaceName],
                });

                // download file to browser
                await DownloadUtils.downloadFile(`${interfaceName}.txt`, new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_export_single"));
                console.error(e);
            }
        },
        async shareInterface(iface) {
            try {
                const response = await window.api.post(apiPath("/reticulum/interfaces/export"), {
                    selected_interface_names: [iface._name],
                });
                const text = typeof response.data === "string" ? response.data : String(response.data || "");
                await copyTextToClipboard(text);
                ToastUtils.success(this.$t("interfaces.copied_share"));
            } catch (e) {
                DialogUtils.alert(this.$t("interfaces.failed_export_single"));
                console.error(e);
            }
        },
        showImportInterfacesModal() {
            this.$refs["import-interfaces-modal"].show();
        },
        onImportInterfacesModalDismissed(imported = false, appliedLive = false) {
            // reload interfaces as something may have been imported
            this.loadInterfaces();
            // imported interfaces are attached live by the backend. Only
            // flag a restart when that did not take.
            if (imported && !appliedLive) {
                this.trackInterfaceChange();
            }
        },
        async loadDiscoveredInterfaces() {
            try {
                const response = await window.api.get(apiPath("/reticulum/discovered-interfaces"));
                const incoming = response.data?.interfaces ?? [];
                const active = response.data?.active ?? [];

                const merged = new Map();
                const existingByKey = new Map();
                this.discoveredInterfaces.forEach((iface) => {
                    existingByKey.set(this.discoveryKey(iface), iface);
                });
                const addOrUpdate = (iface, isNew = false) => {
                    const key = this.discoveryKey(iface);
                    const existing = merged.get(key) || existingByKey.get(key);
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

                // Bound the accumulation: keep the most recently heard entries.
                const mergedList = Array.from(merged.values());
                const cap = this.discoveredInterfacesCap;
                if (mergedList.length > cap) {
                    mergedList.sort((a, b) => (b.last_heard ?? 0) - (a.last_heard ?? 0));
                    mergedList.length = cap;
                }
                this.discoveredInterfaces = mergedList;
                this.discoveredActive = active;
                return true;
            } catch (e) {
                console.log(e);
                return false;
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
            const nid = iface.network_id ? String(iface.network_id).toLowerCase() : null;
            if (iface.transport_id && this.discoveredActiveTransportIds.has(String(iface.transport_id).toLowerCase())) {
                return true;
            }
            const hasMeta = this.discoveryAutoconnectMetadataPresent;
            for (const a of this.discoveredActive || []) {
                const host = a.target_host || a.remote || a.listen_ip;
                const p = a.target_port || a.listen_port;
                if (!host || p == null || !reach || port == null) continue;
                if (String(host) !== String(reach) || Number(p) !== Number(port)) continue;
                const asrc = a.autoconnect_source;
                if (asrc != null && asrc !== undefined) {
                    if (nid !== null && String(asrc).toLowerCase() !== nid) continue;
                    return true;
                }
                if (!hasMeta) return true;
            }
            return this.activeInterfaceStats.some((s) => {
                const hostMatch =
                    (s.target_host && reach && s.target_host === reach) || (s.remote && reach && s.remote === reach);
                const portMatch =
                    (s.target_port && port && Number(s.target_port) === Number(port)) ||
                    (s.listen_port && port && Number(s.listen_port) === Number(port));
                if (!hostMatch || !portMatch || !this.interfaceStatLinkUp(s)) return false;
                const asrc = s.autoconnect_source;
                if (asrc != null && asrc !== undefined) {
                    if (nid !== null) return String(asrc).toLowerCase() === nid;
                    return true;
                }
                return !hasMeta;
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
        interfaceStatLinkUp(s) {
            if (!s || typeof s !== "object") return false;
            if (s.status === false || s.connected === false || s.online === false) return false;
            if (s.status === true || s.connected === true || s.online === true) return true;
            return true;
        },
        discoveredBytes(iface) {
            if (!this.isDiscoveredConnected(iface)) return null;

            const tid = iface.transport_id ? String(iface.transport_id).toLowerCase() : null;
            if (tid) {
                const byTid = (this.discoveredActive || []).find((a) => {
                    if (!a.transport_id) return false;
                    if (String(a.transport_id).toLowerCase() !== tid) return false;
                    return this.interfaceStatLinkUp(a);
                });
                if (byTid && (byTid.txb !== undefined || byTid.rxb !== undefined)) {
                    return {
                        tx: this.formatBytes(byTid.txb ?? 0),
                        rx: this.formatBytes(byTid.rxb ?? 0),
                    };
                }
            }

            const reach = iface.reachable_on;
            const port = iface.port;
            const nid = iface.network_id ? String(iface.network_id).toLowerCase() : null;
            const hasMeta = this.discoveryAutoconnectMetadataPresent;

            const byActive = (this.discoveredActive || []).find((a) => {
                const host = a.target_host || a.remote || a.listen_ip;
                const p = a.target_port || a.listen_port;
                if (!host || p == null || !reach || port == null) return false;
                if (String(host) !== String(reach) || Number(p) !== Number(port)) return false;
                if (!this.interfaceStatLinkUp(a)) return false;
                const asrc = a.autoconnect_source;
                if (asrc != null && asrc !== undefined) {
                    if (nid !== null) return String(asrc).toLowerCase() === nid;
                    return true;
                }
                return !hasMeta;
            });
            if (byActive && (byActive.txb !== undefined || byActive.rxb !== undefined)) {
                return {
                    tx: this.formatBytes(byActive.txb ?? 0),
                    rx: this.formatBytes(byActive.rxb ?? 0),
                };
            }

            const stats = this.activeInterfaceStats || [];
            const match = stats.find((s) => {
                const host = s.target_host || s.remote || s.listen_ip;
                const p = s.target_port || s.listen_port;
                if (!host || !reach || port == null || p == null) return false;
                if (String(host) !== String(reach) || Number(p) !== Number(port)) return false;
                if (!this.interfaceStatLinkUp(s)) return false;
                const asrc = s.autoconnect_source;
                if (asrc != null && asrc !== undefined) {
                    if (nid !== null) return String(asrc).toLowerCase() === nid;
                    return true;
                }
                return !hasMeta;
            });
            if (!match || (match.txb === undefined && match.rxb === undefined)) return null;
            return {
                tx: this.formatBytes(match.txb ?? 0),
                rx: this.formatBytes(match.rxb ?? 0),
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
                const response = await window.api.get(apiPath("/reticulum/discovery"));
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
                        : null;
                this.discoveryConfig.default_gravity =
                    discovery.default_gravity !== undefined &&
                    discovery.default_gravity !== null &&
                    discovery.default_gravity !== ""
                        ? Number(discovery.default_gravity)
                        : null;
                const numericOrNull = (value) =>
                    value !== undefined && value !== null && value !== "" ? Number(value) : null;
                this.discoveryConfig.discovered_interfaces_max_return = numericOrNull(
                    discovery.discovered_interfaces_max_return
                );
                this.discoveryConfig.interface_discovery_unknown_after_days = numericOrNull(
                    discovery.interface_discovery_unknown_after_days
                );
                this.discoveryConfig.interface_discovery_stale_after_days = numericOrNull(
                    discovery.interface_discovery_stale_after_days
                );
                this.discoveryConfig.interface_discovery_remove_after_days = numericOrNull(
                    discovery.interface_discovery_remove_after_days
                );
                this.discoveryConfig.autoconnect_interface_mode = discovery.autoconnect_interface_mode ?? "";
                this.discoveryConfig.autoconnect_interface_gravity =
                    discovery.autoconnect_interface_gravity !== undefined &&
                    discovery.autoconnect_interface_gravity !== null &&
                    discovery.autoconnect_interface_gravity !== ""
                        ? Number(discovery.autoconnect_interface_gravity)
                        : null;
                this.discoveryConfig.autoconnect_announces_to_internal = this.parseBool(
                    discovery.autoconnect_announces_to_internal ?? false
                );
                this.discoveryConfig.autoconnect_unverified_implementations = this.parseBool(
                    discovery.autoconnect_unverified_implementations ?? false
                );
                this.discoveryConfig.default_bootstrap_only = this.parseBool(discovery.default_bootstrap_only ?? false);
                this.discoveryConfig.network_identity = discovery.network_identity ?? "";
            } catch (e) {
                console.log(e);
            }
        },
        async saveDiscoveryConfig() {
            if (this.savingDiscovery) return;
            this.savingDiscovery = true;
            try {
                ToastUtils.loading(this.$t("app.reloading_rns"), 0, "interfaces-discovery-save");
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
                            ? null
                            : Number(this.discoveryConfig.autoconnect_discovered_interfaces),
                    default_gravity:
                        this.discoveryConfig.default_gravity === null || this.discoveryConfig.default_gravity === ""
                            ? null
                            : Number(this.discoveryConfig.default_gravity),
                    autoconnect_interface_mode: this.discoveryConfig.autoconnect_interface_mode || null,
                    autoconnect_interface_gravity:
                        this.discoveryConfig.autoconnect_interface_gravity === null ||
                        this.discoveryConfig.autoconnect_interface_gravity === ""
                            ? null
                            : Number(this.discoveryConfig.autoconnect_interface_gravity),
                    autoconnect_announces_to_internal: this.discoveryConfig.autoconnect_announces_to_internal === true,
                    autoconnect_unverified_implementations:
                        this.discoveryConfig.autoconnect_unverified_implementations === true,
                    default_bootstrap_only: this.discoveryConfig.default_bootstrap_only,
                    discovered_interfaces_max_return:
                        this.discoveryConfig.discovered_interfaces_max_return === null ||
                        this.discoveryConfig.discovered_interfaces_max_return === ""
                            ? null
                            : Number(this.discoveryConfig.discovered_interfaces_max_return),
                    interface_discovery_unknown_after_days:
                        this.discoveryConfig.interface_discovery_unknown_after_days === null ||
                        this.discoveryConfig.interface_discovery_unknown_after_days === ""
                            ? null
                            : Number(this.discoveryConfig.interface_discovery_unknown_after_days),
                    interface_discovery_stale_after_days:
                        this.discoveryConfig.interface_discovery_stale_after_days === null ||
                        this.discoveryConfig.interface_discovery_stale_after_days === ""
                            ? null
                            : Number(this.discoveryConfig.interface_discovery_stale_after_days),
                    interface_discovery_remove_after_days:
                        this.discoveryConfig.interface_discovery_remove_after_days === null ||
                        this.discoveryConfig.interface_discovery_remove_after_days === ""
                            ? null
                            : Number(this.discoveryConfig.interface_discovery_remove_after_days),
                    network_identity: this.discoveryConfig.network_identity || null,
                };

                await window.api.patch(apiPath("/reticulum/discovery"), payload);
                ToastUtils.dismiss("interfaces-discovery-save");
                ToastUtils.success(this.$t("interfaces.discovery_settings_saved"));
                await this.loadDiscoveryConfig();
            } catch (e) {
                ToastUtils.dismiss("interfaces-discovery-save");
                ToastUtils.error(this.$t("interfaces.failed_save_discovery"));
                console.log(e);
            } finally {
                this.savingDiscovery = false;
            }
        },
        async exportDiscoveredInterfaces() {
            if (this.exportingDiscoveredInterfaces) return;
            this.exportingDiscoveredInterfaces = true;
            try {
                const response = await window.api.get(apiPath("/reticulum/discovered-interfaces/export"), {
                    responseType: "blob",
                });
                const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
                await DownloadUtils.downloadFromApiResponse(response, `meshchatx-discovered-interfaces-${stamp}.zip`);
            } catch (e) {
                ToastUtils.error(this.$t("interfaces.discovered_export_failed"));
                console.log(e);
            } finally {
                this.exportingDiscoveredInterfaces = false;
            }
        },
        onImportDiscoveredClick() {
            this.$refs["discovered-import-input"]?.click();
        },
        async onDiscoveredImportFile(event) {
            const file = event?.target?.files?.[0];
            if (event?.target) {
                event.target.value = null;
            }
            if (!file) return;
            this.importingDiscoveredInterfaces = true;
            try {
                const encoded = await this.readFileAsBase64(file);
                const response = await window.api.post(apiPath("/reticulum/discovered-interfaces/import"), {
                    data: encoded,
                });
                const imported = response.data?.imported ?? 0;
                const skipped = response.data?.skipped ?? 0;
                ToastUtils.success(this.$t("interfaces.discovered_import_result", { imported, skipped }));
                await this.refreshDiscoveredInterfacesList();
            } catch (e) {
                ToastUtils.error(this.$t("interfaces.discovered_import_failed"));
                console.log(e);
            } finally {
                this.importingDiscoveredInterfaces = false;
            }
        },
        readFileAsBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    const result = String(reader.result || "");
                    const comma = result.indexOf(",");
                    resolve(comma >= 0 ? result.slice(comma + 1) : result);
                };
                reader.onerror = () => reject(reader.error || new Error("file read failed"));
                reader.readAsDataURL(file);
            });
        },
        toggleDiscoveryActionsMenu(iface) {
            const key = this.discoveryKey(iface);
            this.openDiscoveryActionKey = this.openDiscoveryActionKey === key ? null : key;
        },
        closeDiscoveryActionsMenu() {
            this.openDiscoveryActionKey = null;
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
                await window.api.patch(apiPath("/reticulum/discovery"), payload);
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
        discoveredNetworkName(iface) {
            if (!iface) return null;
            return iface.network_name || iface.ifac_netname || null;
        },
        discoveredPassphrase(iface) {
            if (!iface) return null;
            return iface.passphrase || iface.ifac_netkey || null;
        },
        maskPassphrase(value) {
            if (!value) return "";
            const str = String(value);
            if (str.length <= 4) return "*".repeat(str.length);
            return `${str.slice(0, 2)}${"*".repeat(Math.max(4, str.length - 4))}${str.slice(-2)}`;
        },
        copyDiscoveredConfigEntry(iface) {
            this.openDiscoveryActionKey = null;
            const entry = iface?.config_entry;
            if (!entry) {
                ToastUtils.error(this.$t("interfaces.discovered_no_config"));
                return;
            }
            this.copyToClipboard(entry, this.$t("interfaces.discovered_config_block"));
        },
        useDiscoveredInterface(iface) {
            this.openDiscoveryActionKey = null;
            if (!iface) return;
            const prefill = {
                name: iface.name || "",
                type: iface.type || null,
                target_host: iface.reachable_on || iface.target_host || iface.remote || null,
                target_port: iface.port || iface.target_port || null,
                transport_identity: iface.transport_id || iface.transport_identity || null,
                network_name: this.discoveredNetworkName(iface),
                passphrase: this.discoveredPassphrase(iface),
                discoverable: iface.discoverable || null,
                config_entry: iface.config_entry || null,
                frequency: iface.frequency ?? null,
                bandwidth: iface.bandwidth ?? null,
                spreadingfactor: iface.sf ?? iface.spreadingfactor ?? null,
                codingrate: iface.cr ?? iface.codingrate ?? null,
                latitude: iface.latitude ?? null,
                longitude: iface.longitude ?? null,
                height: iface.height ?? null,
            };
            try {
                if (typeof sessionStorage !== "undefined") {
                    sessionStorage.setItem("meshchatx.discoveredInterfacePrefill", JSON.stringify(prefill));
                }
            } catch (e) {
                console.log(e);
            }
            this.$router.push({
                name: "interfaces.add",
                query: { from_discovered: "1" },
            });
        },

        async refreshDiscoveredInterfacesList() {
            const ok = await this.loadDiscoveredInterfaces();
            if (ok) {
                ToastUtils.success(this.$t("interfaces.discovery_list_refreshed"));
            } else {
                ToastUtils.error(this.$t("interfaces.discovery_list_refresh_failed"));
            }
        },
        filterChipClass(isActive) {
            return isActive ? "primary-chip text-xs" : "secondary-chip text-xs";
        },
        async reloadRns() {
            if (this.reloadingRns) return;

            try {
                this.reloadingRns = true;
                ToastUtils.loading(this.$t("app.reloading_rns"), 0, "interfaces-rns-reload");
                const response = await window.api.post(apiPath("/reticulum/reload"));
                ToastUtils.success(response.data.message);
                useInterfaceChangesStore().hasPendingInterfaceChanges = false;
                useInterfaceChangesStore().modifiedInterfaceNames.clear();
                await this.loadInterfaces();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("interfaces.failed_reload"));
                console.error(e);
            } finally {
                ToastUtils.dismiss("interfaces-rns-reload");
                this.reloadingRns = false;
            }
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.interfaces-section {
    @apply w-full border-b border-sem-border dark:border-sem-border py-4 sm:py-6;
}
.interfaces-section--hero {
    @apply border-b border-sem-border dark:border-sem-border py-4 sm:py-6;
}
.interfaces-subpanel {
    @apply mt-4 pt-4 border-t border-sem-border dark:border-sem-border first:mt-0 first:pt-0 first:border-0;
}
.fill-up::before {
    content: "";
    position: absolute;
    inset: 0;
    background: currentColor;
    opacity: 0.15;
    border-radius: inherit;
    animation: fillUp 1.5s ease-in-out infinite;
    pointer-events: none;
}
@keyframes fillUp {
    0% {
        clip-path: inset(100% 0 0 0);
    }
    50% {
        clip-path: inset(0% 0 0 0);
    }
    100% {
        clip-path: inset(0% 0 0 0);
    }
}
</style>
