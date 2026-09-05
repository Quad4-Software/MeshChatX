<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { SvelteSet } from "svelte/reactivity";
    import ToastUtils from "../../js/ToastUtils.js";
    import DownloadUtils from "../../js/DownloadUtils.js";
    import ElectronUtils from "../../js/ElectronUtils.js";
    import GlobalState from "../../js/GlobalState.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";
    import { BATTERY_SAVER_CHANGED_EVENT, loadBatterySaverPrefs } from "../../js/settings/batterySaverPrefs.js";
    import { INTERFACES_ADD_ROUTE_NAME, INTERFACES_EDIT_ROUTE_NAME } from "./lib/constants.js";
    import type {
        ConfiguredInterface,
        DiscoveredInterface,
        DiscoveredActiveInterface,
        DiscoveryConfig,
        InterfaceStats,
    } from "./lib/types.js";
    import {
        fetchInterfaces,
        fetchInterfaceStats,
        enableInterfaceApi,
        disableInterfaceApi,
        deleteInterfaceApi,
        exportInterfaceApi,
        exportAllInterfacesApi,
        reloadRnsApi,
        fetchDiscoveryConfigApi,
        saveDiscoveryConfigApi,
        fetchDiscoveredInterfacesApi,
        fetchAppInfoApi,
    } from "./lib/interfacesApi.js";
    import {
        isInterfaceEnabled,
        isDiscoveredConnected,
        discoveryPatternToken,
        normalizeDiscoveryPatternInput,
        discoveredNetworkName,
        discoveredPassphrase,
    } from "./lib/interfacesFormat.js";

    import InterfaceCard from "./components/InterfaceCard.svelte";
    import DiscoveredInterfaceCard from "./components/DiscoveredInterfaceCard.svelte";
    import DiscoverySettingsPanel from "./components/DiscoverySettingsPanel.svelte";
    import ImportInterfacesModal from "./components/ImportInterfacesModal.svelte";
    import InterfacesHeroSection from "./components/InterfacesHeroSection.svelte";

    let interfaces = $state<Record<string, ConfiguredInterface>>({});
    let interfaceStats = $state<Record<string, InterfaceStats>>({});
    let discoveredInterfaces = $state<DiscoveredInterface[]>([]);
    let discoveredActive = $state<DiscoveredActiveInterface[]>([]);

    let searchTerm = $state("");
    let statusFilter = $state<"all" | "enabled" | "disabled">("all");
    let typeFilter = $state("all");
    let discoveredStatusFilter = $state<"all" | "connected">("all");
    let activeTab = $state<"overview" | "discovery">("overview");

    let isReticulumRunning = $state(true);
    let reloadingRns = $state(false);
    let savingDiscoveryConfig = $state(false);
    let savingDiscoveryAction = $state(false);
    let openDiscoveryActionKey = $state<string | null>(null);

    let isImportModalShowing = $state(false);

    let discoveryConfig = $state<DiscoveryConfig>({
        discover_interfaces: false,
        autodiscover_allow_all: false,
        autodiscover_list: "",
        autodiscover_blacklist: "",
        autodiscover_default_bootstrap_only: false,
    });

    let reloadInterval: ReturnType<typeof setInterval> | null = null;
    let discoveryInterval: ReturnType<typeof setInterval> | null = null;
    let batterySaverHandler: (() => void) | null = null;

    const isElectron = $derived(ElectronUtils.isElectron());
    const hasPendingChanges = $derived(GlobalState.hasPendingInterfaceChanges);
    const modifiedNames = $derived(GlobalState.modifiedInterfaceNames);

    const interfacesWithStats = $derived.by(() => {
        const results: ConfiguredInterface[] = [];
        for (const [name, iface] of Object.entries(interfaces)) {
            const item = { ...iface };
            item._name = name;
            item._stats = interfaceStats[name];
            item._restart_required = modifiedNames.has(name);
            results.push(item);
        }
        return results;
    });

    const sortedInterfaceTypes = $derived.by(() => {
        const types = new SvelteSet<string>();
        interfacesWithStats.forEach((iface) => {
            if (iface.type) types.add(iface.type);
        });
        return Array.from(types).sort();
    });

    const filteredInterfaces = $derived.by(() => {
        const search = searchTerm.toLowerCase().trim();
        return interfacesWithStats
            .filter((iface) => {
                if (statusFilter === "enabled" && !isInterfaceEnabled(iface)) return false;
                if (statusFilter === "disabled" && isInterfaceEnabled(iface)) return false;
                if (typeFilter !== "all" && iface.type !== typeFilter) return false;
                if (!search) return true;
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
                const diff = Number(isInterfaceEnabled(b)) - Number(isInterfaceEnabled(a));
                if (diff !== 0) return diff;
                return (a._name || "").localeCompare(b._name || "");
            });
    });

    const activeTransportIds = $derived.by(() => {
        const set = new SvelteSet<string>();
        discoveredActive.forEach((a) => {
            if (a.transport_id) set.add(String(a.transport_id).toLowerCase());
        });
        return set;
    });

    const metadataPresent = $derived.by(() => {
        const fromActive = (discoveredActive || []).some((a) => a.autoconnect_source != null);
        const fromStats = Object.values(interfaceStats || {}).some((s) => s.autoconnect_source != null);
        return fromActive || fromStats;
    });

    const sortedDiscoveredInterfaces = $derived.by(() => {
        const search = searchTerm.toLowerCase().trim();
        let list = [...discoveredInterfaces];
        if (discoveredStatusFilter === "connected") {
            list = list.filter((iface) =>
                isDiscoveredConnected(
                    iface,
                    discoveredActive,
                    Object.values(interfaceStats),
                    activeTransportIds,
                    metadataPresent
                )
            );
        }
        if (typeFilter !== "all") {
            list = list.filter((iface) => iface.type === typeFilter);
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
    });

    const interfacesWithLocation = $derived(
        discoveredInterfaces.filter((iface) => iface.latitude != null && iface.longitude != null)
    );

    onMount(() => {
        try {
            const sf = localStorage.getItem("meshchatx.interfaces.statusFilter");
            if (sf === "all" || sf === "enabled" || sf === "disabled") {
                statusFilter = sf;
            }
            const df = localStorage.getItem("meshchatx.interfaces.discoveredStatusFilter");
            if (df === "all" || df === "connected") {
                discoveredStatusFilter = df;
            }
        } catch {
            /* ignore */
        }

        loadAllData();

        batterySaverHandler = () => {
            startPollIntervals();
        };
        GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, batterySaverHandler);
        GlobalEmitter.on("identity-switched", handleIdentitySwitched);
        GlobalEmitter.on("websocket-reconnected", handleWebsocketReconnected);

        startPollIntervals();
    });

    onDestroy(() => {
        stopPollIntervals();
        if (batterySaverHandler) {
            GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, batterySaverHandler);
        }
        GlobalEmitter.off("identity-switched", handleIdentitySwitched);
        GlobalEmitter.off("websocket-reconnected", handleWebsocketReconnected);
    });

    $effect(() => {
        try {
            localStorage.setItem("meshchatx.interfaces.statusFilter", statusFilter);
        } catch {
            /* ignore */
        }
    });

    $effect(() => {
        try {
            localStorage.setItem("meshchatx.interfaces.discoveredStatusFilter", discoveredStatusFilter);
        } catch {
            /* ignore */
        }
    });

    function handleIdentitySwitched() {
        loadInterfaces();
        updateStats();
        loadDiscoveryConfig();
        loadDiscovered();
    }

    function handleWebsocketReconnected() {
        loadAllData();
    }

    async function loadAllData() {
        loadInterfaces();
        updateStats();
        loadDiscoveryConfig();
        loadDiscovered();
    }

    async function loadInterfaces() {
        try {
            const res = await fetchInterfaces();
            interfaces = res.interfaces || {};
            const info = await fetchAppInfoApi();
            isReticulumRunning = info.isReticulumRunning !== false;
        } catch {
            /* ignore */
        }
    }

    async function updateStats() {
        try {
            const stats = await fetchInterfaceStats();
            interfaceStats = stats;
        } catch {
            /* ignore */
        }
    }

    async function loadDiscoveryConfig() {
        try {
            const cfg = await fetchDiscoveryConfigApi();
            discoveryConfig = cfg;
        } catch {
            /* ignore */
        }
    }

    async function loadDiscovered() {
        try {
            const res = await fetchDiscoveredInterfacesApi();
            discoveredInterfaces = res.interfaces || [];
            discoveredActive = res.active || [];
        } catch {
            /* ignore */
        }
    }

    function startPollIntervals() {
        stopPollIntervals();
        const prefs = loadBatterySaverPrefs();
        const liveReady = GlobalState.liveTransportReady === true;
        let statsMs = prefs.enabled && prefs.reduceInterfacesDiscovery ? prefs.interfacesStatsPollSeconds * 1000 : 1000;
        let discoveryMs =
            prefs.enabled && prefs.reduceInterfacesDiscovery ? prefs.interfacesDiscoveryPollSeconds * 1000 : 5000;
        if (liveReady) {
            statsMs = Math.max(statsMs, 15000);
            discoveryMs = Math.max(discoveryMs, 30000);
        }
        reloadInterval = setInterval(updateStats, statsMs);
        discoveryInterval = setInterval(loadDiscovered, discoveryMs);
    }

    function stopPollIntervals() {
        if (reloadInterval) clearInterval(reloadInterval);
        if (discoveryInterval) clearInterval(discoveryInterval);
        reloadInterval = null;
        discoveryInterval = null;
    }

    async function handleEnable(name: string) {
        try {
            await enableInterfaceApi(name);
            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.add(name);
            ToastUtils.showSuccess(`Enabled ${name}`);
            loadInterfaces();
        } catch (err: any) {
            ToastUtils.showError(err?.message || `Failed to enable ${name}`);
        }
    }

    async function handleDisable(name: string) {
        try {
            await disableInterfaceApi(name);
            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.add(name);
            ToastUtils.showSuccess(`Disabled ${name}`);
            loadInterfaces();
        } catch (err: any) {
            ToastUtils.showError(err?.message || `Failed to disable ${name}`);
        }
    }

    async function handleDelete(name: string) {
        if (!confirm(`Are you sure you want to delete interface "${name}"?`)) return;
        try {
            await deleteInterfaceApi(name);
            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.delete(name);
            ToastUtils.showSuccess(`Deleted ${name}`);
            loadInterfaces();
        } catch (err: any) {
            ToastUtils.showError(err?.message || `Failed to delete ${name}`);
        }
    }

    async function handleExport(name: string) {
        try {
            const data = await exportInterfaceApi(name);
            await DownloadUtils.downloadFile(`interface-${name}.json`, data);
            ToastUtils.showSuccess(`Exported ${name}`);
        } catch (err: any) {
            ToastUtils.showError(err?.message || `Failed to export ${name}`);
        }
    }

    async function handleExportAll() {
        try {
            const data = await exportAllInterfacesApi();
            await DownloadUtils.downloadFile("interfaces-all.json", data);
            ToastUtils.showSuccess("Exported all interfaces");
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to export interfaces");
        }
    }

    async function handleReloadRns() {
        if (reloadingRns) return;
        reloadingRns = true;
        try {
            ToastUtils.loading(t("app.reloading_rns"), 0, "interfaces-rns-reload");
            const res = await reloadRnsApi();
            GlobalState.hasPendingInterfaceChanges = false;
            GlobalState.modifiedInterfaceNames.clear();
            ToastUtils.success(res.message);
            await loadAllData();
        } catch (err: any) {
            ToastUtils.error(err?.message || t("interfaces.failed_reload"));
        } finally {
            ToastUtils.dismiss("interfaces-rns-reload");
            reloadingRns = false;
        }
    }

    function handleRelaunch() {
        ElectronUtils.relaunch();
    }

    function handleEdit(name: string) {
        window.location.hash = `#/${INTERFACES_EDIT_ROUTE_NAME}?name=${encodeURIComponent(name)}`;
    }

    function handleAdd() {
        window.location.hash = `#/${INTERFACES_ADD_ROUTE_NAME}`;
    }

    async function handleSaveDiscoverySettings() {
        savingDiscoveryConfig = true;
        try {
            await saveDiscoveryConfigApi(discoveryConfig);
            ToastUtils.showSuccess(t("interfaces.discovery_settings_saved"));
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to save discovery settings");
        } finally {
            savingDiscoveryConfig = false;
        }
    }

    function handleMapAllDiscovered() {
        window.location.hash = `#/map?tab=discovered`;
    }

    function handleUseDiscovered(iface: DiscoveredInterface) {
        openDiscoveryActionKey = null;
        const prefill = {
            name: iface.name || null,
            type: iface.type || null,
            target_host: iface.reachable_on || iface.target_host || iface.remote || null,
            target_port: iface.port || iface.target_port || null,
            transport_identity: iface.transport_id || null,
            network_name: discoveredNetworkName(iface),
            passphrase: discoveredPassphrase(iface),
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
        } catch {
            /* ignore */
        }
        window.location.hash = `#/${INTERFACES_ADD_ROUTE_NAME}?from_discovered=1`;
    }

    function handleCopyDiscoveredConfig(iface: DiscoveredInterface) {
        openDiscoveryActionKey = null;
        if (!iface || !iface.config_entry) {
            ToastUtils.error("No config entry available for this interface");
            return;
        }
        navigator.clipboard.writeText(iface.config_entry);
        ToastUtils.success("Config entry copied to clipboard");
    }

    async function handleAddToList(iface: DiscoveredInterface, action: "allow" | "block") {
        openDiscoveryActionKey = null;
        savingDiscoveryAction = true;
        try {
            const token = discoveryPatternToken(iface);
            if (!token) return;
            const whitelist = normalizeDiscoveryPatternInput(discoveryConfig.interface_discovery_whitelist);
            const blacklist = normalizeDiscoveryPatternInput(discoveryConfig.interface_discovery_blacklist);
            const tokenLower = token.toLowerCase();
            const dedupe = (list: string[]) =>
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

            const payload: Record<string, unknown> = {
                interface_discovery_whitelist: nextWhitelist.length ? nextWhitelist.join(",") : null,
                interface_discovery_blacklist: nextBlacklist.length ? nextBlacklist.join(",") : null,
            };
            await saveDiscoveryConfigApi(payload);
            discoveryConfig.interface_discovery_whitelist = (payload.interface_discovery_whitelist as string) || "";
            discoveryConfig.interface_discovery_blacklist = (payload.interface_discovery_blacklist as string) || "";
            ToastUtils.success(
                action === "allow" ? `Added ${token} to discovery whitelist` : `Added ${token} to discovery blacklist`
            );
        } catch (err: any) {
            ToastUtils.error(err?.message || "Failed to update list");
        } finally {
            savingDiscoveryAction = false;
        }
    }

    function handleCopyText(text: string, label: string) {
        navigator.clipboard.writeText(text);
        ToastUtils.showSuccess(`Copied ${label} to clipboard`);
    }

    function handleGoToMap(iface: DiscoveredInterface) {
        if (iface.latitude != null && iface.longitude != null) {
            window.location.hash = `#/map?lat=${iface.latitude}&lon=${iface.longitude}`;
        }
    }
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas text-sem-fg">
    <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4">
        <div class="space-y-0 w-full min-w-0 max-w-6xl xl:max-w-7xl 2xl:max-w-360 mx-auto flex-1">
            <InterfacesHeroSection
                {hasPendingChanges}
                {isElectron}
                {reloadingRns}
                {searchTerm}
                {typeFilter}
                {sortedInterfaceTypes}
                onrelaunch={handleRelaunch}
                onadd={handleAdd}
                onimport={() => (isImportModalShowing = true)}
                onexportall={handleExportAll}
                onreloadrns={handleReloadRns}
                onsearchchange={(v) => (searchTerm = v)}
                ontypechange={(v) => (typeFilter = v)}
            />

            <!-- Tab Navigation & Content -->
            <div class="interfaces-section space-y-4">
                <div class="flex flex-wrap gap-2">
                    <button
                        type="button"
                        class={activeTab === "overview" ? "primary-chip text-xs" : "secondary-chip text-xs"}
                        onclick={() => (activeTab = "overview")}
                    >
                        Overview
                    </button>
                    <button
                        type="button"
                        class={activeTab === "discovery" ? "primary-chip text-xs" : "secondary-chip text-xs"}
                        onclick={() => (activeTab = "discovery")}
                    >
                        Discovery Settings
                    </button>
                </div>

                {#if activeTab === "overview"}
                    <div class="space-y-4">
                        <!-- Configured Interfaces Grid -->
                        <div class="interfaces-subpanel space-y-3">
                            <div class="flex flex-wrap items-center justify-between gap-4">
                                <div class="space-y-1">
                                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">Configured</div>
                                    <div class="text-xl font-semibold text-sem-fg">
                                        Interfaces
                                        {#if filteredInterfaces.length > 0}
                                            <span class="ml-2 text-sm font-medium text-gray-400"
                                                >({filteredInterfaces.length})</span
                                            >
                                        {/if}
                                    </div>
                                </div>
                                <div class="flex gap-2 flex-wrap">
                                    <button
                                        type="button"
                                        class="py-1! px-3! {statusFilter === 'all'
                                            ? 'primary-chip text-xs'
                                            : 'secondary-chip text-xs'}"
                                        onclick={() => (statusFilter = "all")}
                                    >
                                        {t("interfaces.all")}
                                    </button>
                                    <button
                                        type="button"
                                        class="py-1! px-3! {statusFilter === 'enabled'
                                            ? 'primary-chip text-xs'
                                            : 'secondary-chip text-xs'}"
                                        onclick={() => (statusFilter = "enabled")}
                                    >
                                        {t("app.enabled")}
                                    </button>
                                    <button
                                        type="button"
                                        class="py-1! px-3! {statusFilter === 'disabled'
                                            ? 'primary-chip text-xs'
                                            : 'secondary-chip text-xs'}"
                                        onclick={() => (statusFilter = "disabled")}
                                    >
                                        {t("app.disabled")}
                                    </button>
                                </div>
                            </div>

                            {#if filteredInterfaces.length > 0}
                                <div class="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3 3xl:grid-cols-4 4xl:grid-cols-5">
                                    {#each filteredInterfaces as iface (iface._name)}
                                        <InterfaceCard
                                            {iface}
                                            {isReticulumRunning}
                                            showRestartBanner={hasPendingChanges}
                                            onenable={() => handleEnable(iface._name)}
                                            ondisable={() => handleDisable(iface._name)}
                                            onedit={() => handleEdit(iface._name)}
                                            onexport={() => handleExport(iface._name)}
                                            ondelete={() => handleDelete(iface._name)}
                                        />
                                    {/each}
                                </div>
                            {:else}
                                <div
                                    class="text-center py-10 px-4 text-gray-500 dark:text-gray-300 border border-dashed border-sem-border rounded-xl"
                                >
                                    <MaterialDesignIcon iconName="lan-disconnect" class="w-10 h-10 mx-auto mb-3" />
                                    <div class="text-lg font-semibold">{t("interfaces.no_interfaces_found")}</div>
                                    <div class="text-sm">{t("interfaces.no_interfaces_description")}</div>
                                </div>
                            {/if}
                        </div>

                        <!-- Discovered Interfaces Section -->
                        <div class="interfaces-subpanel space-y-3">
                            <div class="flex flex-col gap-3 min-w-0 lg:flex-row lg:items-start lg:justify-between">
                                <div class="min-w-0 flex-1">
                                    <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                                        Discovered Interfaces
                                    </div>
                                    <div class="text-xl font-semibold text-sem-fg">
                                        Recently Heard Announces
                                        {#if sortedDiscoveredInterfaces.length > 0}
                                            <span class="ml-2 text-sm font-medium text-gray-400"
                                                >({sortedDiscoveredInterfaces.length})</span
                                            >
                                        {/if}
                                    </div>
                                    <div class="text-sm text-sem-fg-muted">
                                        Discovery runs continually. Heard announces stay listed. Connected entries show
                                        a green pill.
                                    </div>
                                </div>
                                <div class="flex flex-wrap gap-2 items-center shrink-0 min-w-0">
                                    <div class="flex gap-1.5 mr-2">
                                        <button
                                            type="button"
                                            class="py-1! px-3! {discoveredStatusFilter === 'all'
                                                ? 'primary-chip text-xs'
                                                : 'secondary-chip text-xs'}"
                                            onclick={() => (discoveredStatusFilter = "all")}
                                        >
                                            {t("interfaces.all")}
                                        </button>
                                        <button
                                            type="button"
                                            class="py-1! px-3! {discoveredStatusFilter === 'connected'
                                                ? 'primary-chip text-xs'
                                                : 'secondary-chip text-xs'}"
                                            onclick={() => (discoveredStatusFilter = "connected")}
                                        >
                                            {t("interfaces.connected_only")}
                                        </button>
                                    </div>
                                    {#if interfacesWithLocation.length > 0}
                                        <button
                                            type="button"
                                            class="secondary-chip text-xs bg-blue-500/10 hover:bg-blue-500/20 text-sem-accent border-blue-500/30"
                                            onclick={handleMapAllDiscovered}
                                        >
                                            <MaterialDesignIcon iconName="map-marker-multiple" class="w-4 h-4" />
                                            <span>Map All ({interfacesWithLocation.length})</span>
                                        </button>
                                    {/if}
                                    <button type="button" class="secondary-chip text-xs" onclick={loadDiscovered}>
                                        <MaterialDesignIcon iconName="refresh" class="w-4 h-4" />
                                        <span>Refresh</span>
                                    </button>
                                </div>
                            </div>

                            {#if sortedDiscoveredInterfaces.length > 0}
                                <div class="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3 3xl:grid-cols-4 4xl:grid-cols-5">
                                    {#each sortedDiscoveredInterfaces as iface (iface.name + (iface.reachable_on || "") + (iface.port || ""))}
                                        <DiscoveredInterfaceCard
                                            {iface}
                                            activeList={discoveredActive}
                                            statsList={Object.values(interfaceStats)}
                                            {activeTransportIds}
                                            {metadataPresent}
                                            blacklistStr={discoveryConfig.autodiscover_blacklist}
                                            isOpenActionMenu={openDiscoveryActionKey ===
                                                iface.name + (iface.reachable_on || "")}
                                            {savingDiscoveryAction}
                                            ontogglemenu={() => {
                                                const k = iface.name + (iface.reachable_on || "");
                                                openDiscoveryActionKey = openDiscoveryActionKey === k ? null : k;
                                            }}
                                            onusediscovered={() => handleUseDiscovered(iface)}
                                            oncopydiscoveredconfig={() => handleCopyDiscoveredConfig(iface)}
                                            onaddtolist={(act) => handleAddToList(iface, act)}
                                            ongotomap={() => handleGoToMap(iface)}
                                            oncopytext={handleCopyText}
                                        />
                                    {/each}
                                </div>
                            {:else}
                                <div class="text-sm text-sem-fg-muted py-4">
                                    {!isReticulumRunning
                                        ? "LXMF/Reticulum is not running. Discovery cannot listen for announces."
                                        : !discoveryConfig.discover_interfaces
                                          ? "Discovery is disabled. Enable it to start listening for announces."
                                          : "Discovery is working, be patient while it waits for announces."}
                                </div>
                            {/if}
                        </div>
                    </div>
                {:else}
                    <!-- Discovery Settings Tab -->
                    <DiscoverySettingsPanel
                        bind:discoveryConfig
                        {savingDiscoveryConfig}
                        onsave={handleSaveDiscoverySettings}
                    />
                {/if}
            </div>
        </div>
    </div>

    <!-- Mobile Floating Action Button -->
    <button
        type="button"
        class="fixed bottom-6 right-6 z-40 sm:hidden primary-btn rounded-full w-14 h-14 shadow-2xl flex items-center justify-center p-0"
        aria-label={t("interfaces.add_interface")}
        onclick={handleAdd}
    >
        <MaterialDesignIcon iconName="plus" class="w-7 h-7" />
    </button>

    <!-- Import Interfaces Modal -->
    <ImportInterfacesModal
        bind:isShowing={isImportModalShowing}
        ondismissed={(imported) => {
            if (imported) loadInterfaces();
        }}
    />
</div>
