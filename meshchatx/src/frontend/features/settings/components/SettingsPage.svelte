<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SettingsNav from "./SettingsNav.svelte";
    import MicronWasmUpdateModal from "./MicronWasmUpdateModal.svelte";
    import NotificationSoundSettings from "./NotificationSoundSettings.svelte";

    // Section leaf components
    import LanguageSettingsSection from "./sections/LanguageSettingsSection.svelte";
    import AppearanceSettingsSection from "./sections/AppearanceSettingsSection.svelte";
    import BatterySettingsSection from "./sections/BatterySettingsSection.svelte";
    import ExperimentalLiveSettingsSection from "./sections/ExperimentalLiveSettingsSection.svelte";
    import DesktopSettingsSection from "./sections/DesktopSettingsSection.svelte";
    import AndroidSettingsSection from "./sections/AndroidSettingsSection.svelte";
    import ShortcutsSettingsSection from "./sections/ShortcutsSettingsSection.svelte";
    import LocationSettingsSection from "./sections/LocationSettingsSection.svelte";
    import StrangerProtectionSettingsSection from "./sections/StrangerProtectionSettingsSection.svelte";
    import MessagesSettingsSection from "./sections/MessagesSettingsSection.svelte";
    import PropagationSettingsSection from "./sections/PropagationSettingsSection.svelte";
    import StickersSettingsSection from "./sections/StickersSettingsSection.svelte";
    import GifsSettingsSection from "./sections/GifsSettingsSection.svelte";
    import TransportSettingsSection from "./sections/TransportSettingsSection.svelte";
    import InterfacesSettingsSection from "./sections/InterfacesSettingsSection.svelte";
    import VisualiserSettingsSection from "./sections/VisualiserSettingsSection.svelte";
    import CrawlerSettingsSection from "./sections/CrawlerSettingsSection.svelte";
    import NetworkSecuritySettingsSection from "./sections/NetworkSecuritySettingsSection.svelte";
    import TelephonySettingsSection from "./sections/TelephonySettingsSection.svelte";
    import ArchiverSettingsSection from "./sections/ArchiverSettingsSection.svelte";
    import NomadRendererSettingsSection from "./sections/NomadRendererSettingsSection.svelte";
    import PrivacyDataSettingsSection from "./sections/PrivacyDataSettingsSection.svelte";
    import BlockedSettingsSection from "./sections/BlockedSettingsSection.svelte";
    import BanishmentSettingsSection from "./sections/BanishmentSettingsSection.svelte";
    import AuthSettingsSection from "./sections/AuthSettingsSection.svelte";
    import WebExposureSettingsSection from "./sections/WebExposureSettingsSection.svelte";
    import CspSettingsSection from "./sections/CspSettingsSection.svelte";
    import MaintenanceSettingsSection from "./sections/MaintenanceSettingsSection.svelte";
    import SelftestSettingsSection from "./sections/SelftestSettingsSection.svelte";
    import InfrastructureSettingsSection from "./sections/InfrastructureSettingsSection.svelte";
    import PluginsSettingsSection from "./sections/PluginsSettingsSection.svelte";
    import ReticulumStackSettingsSection from "./sections/ReticulumStackSettingsSection.svelte";

    import ToastUtils from "../../../js/ToastUtils.js";
    import ElectronUtils from "../../../js/ElectronUtils.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { t } from "../../../js/i18n.js";
    import {
        fetchMergedConfig,
        patchServerConfig,
        publishPatchedConfig,
        sanitizeColorConfigFields,
    } from "../../../js/settings/settingsConfigService.js";
    import {
        fetchReticulumInstanceSettings,
        applyReticulumInstanceSettings,
        applyTransportMode,
    } from "../../../js/settings/settingsTransportService.js";
    import {
        loadVisualiserDisplayPrefs,
        persistVisualiserShowDisabled,
        persistVisualiserShowDiscovered,
        persistVisualiserRenderer,
        persistVisualiserViewMode,
        normalizeVisualiserRenderer,
        normalizeVisualiserViewMode,
    } from "../../../js/settings/settingsVisualiserPrefs.js";
    import {
        ALL_SETTINGS_SECTIONS,
        DEFAULT_SETTINGS_TAB,
        normalizeSettingsTabId,
        SETTINGS_TABS,
        settingsSectionBelongsToTab,
        settingsSectionSearchExtras,
    } from "../../../js/settings/settingsTabs.js";
    import { matchesSettingSearch, normalizeSearchString } from "../../../js/settingsSearchUtils.js";
    import { getAllSettingsSectionKeywords } from "../../../js/registries/settingsSectionRegistry.js";
    import { isMicronWasmBundled } from "../../../js/MicronWasmLoader.js";
    import { getEffectiveMicronWasmReleaseLabel } from "../../../js/micronWasmVersion.js";
    import { setLocale } from "../../../js/localeLoader.js";

    import {
        createDefaultConfig,
        createDefaultReticulumInstance,
        createDefaultServerSecurity,
    } from "../lib/settingsDefaults.js";
    import {
        fetchDesktopCloseSettings,
        fetchScreenSecuritySettings,
        applyScreenSecurityChange,
        applyDesktopTrayEnabledChange,
        applyDesktopCloseBehaviorChange,
    } from "../lib/settingsDesktopHelpers.js";
    import {
        resetAppearanceDefaults as resetAppearanceDefaultsHelper,
        handleDetailedOutboundSendStatusChange,
        handleOutboundTransferProgressEnabledChange,
        handleMessageTimestampGroupingChange,
        savePreferredPropagationNodeHash as savePreferredPropagationNodeHashHelper,
        flushArchivedPages as flushArchivedPagesHelper,
        revokeTelemetryTrust as revokeTelemetryTrustHelper,
    } from "../lib/settingsPageHelpers.js";

    let config = $state<Record<string, any>>(createDefaultConfig());
    let serverSecurity = $state<Record<string, any>>(createDefaultServerSecurity());
    let reticulumInstance = $state<Record<string, any>>(createDefaultReticulumInstance());
    let reticulumInstanceSaving = $state(false);
    let trustedTelemetryPeers = $state<any[]>([]);
    let searchQuery = $state("");
    let searchTabFilter = $state<string | null>(null);
    let activeSettingsTab = $state(DEFAULT_SETTINGS_TAB);
    let micronWasmUpdateModalOpen = $state(false);
    let micronReleaseLabel = $state("v1.0.0");
    let isWasmBundled = $state(true);
    let reloadingRns = $state(false);
    let reloadRnsStatusMessage = $state("");

    let exposureAckFirewall = $state(false);
    let exposureAckVpn = $state(false);
    let showWindowsScreenSecurity = $state(false);
    let screenSecurityEnabled = $state(false);
    let screenSecuritySaving = $state(false);
    let desktopCloseSettings = $state<{ trayEnabled?: boolean; closeBehavior?: string }>({
        trayEnabled: true,
        closeBehavior: "ask",
    });
    let visualiserDisplayPrefs = $state(loadVisualiserDisplayPrefs());

    let lastRememberedInboundStampCost = $state(8);
    const inboundStampsEnabled = $derived(
        Boolean(config.lxmf_inbound_stamp_cost && Number(config.lxmf_inbound_stamp_cost) > 0)
    );

    const isSearching = $derived(Boolean(normalizeSearchString(searchQuery)));

    const matchingSectionKeys = $derived.by(() => {
        const query = normalizeSearchString(searchQuery);
        if (!query) return new Set<string>();
        const keywordsBySection = getAllSettingsSectionKeywords();
        const matches = new Set<string>();
        for (const sectionKey of ALL_SETTINGS_SECTIONS) {
            const keywords = keywordsBySection[sectionKey] || [];
            const extras = settingsSectionSearchExtras(sectionKey);
            const texts = [...keywords, ...extras];
            if (matchesSettingSearch(texts, (k) => t(k), searchQuery)) {
                matches.add(sectionKey);
            }
        }
        return matches;
    });

    const matchCounts = $derived.by(() => {
        if (!isSearching) return null;
        const counts: Record<string, number> = {};
        for (const tab of SETTINGS_TABS) {
            counts[tab.id] = tab.sections.filter((sectionKey) => matchingSectionKeys.has(sectionKey)).length;
        }
        return counts;
    });

    const hasSearchResults = $derived(!isSearching || matchingSectionKeys.size > 0);

    function showSection(sectionKey: string): boolean {
        if (isSearching) {
            if (searchTabFilter && !settingsSectionBelongsToTab(sectionKey, searchTabFilter)) {
                return false;
            }
            return matchingSectionKeys.has(sectionKey);
        }
        return settingsSectionBelongsToTab(sectionKey, activeSettingsTab);
    }

    async function loadConfig() {
        try {
            const merged = await fetchMergedConfig(window.api, config);
            if (merged) {
                sanitizeColorConfigFields(merged);
                config = merged;
            }
        } catch (e) {
            console.error("Failed to load config", e);
        }
    }

    async function loadServerSecurity() {
        try {
            const response = await window.api.get("/api/v1/server/security-info");
            serverSecurity = { ...serverSecurity, ...response.data };
        } catch (e) {
            console.error("Failed to load server security info", e);
        }
    }

    async function loadReticulumInstance() {
        try {
            const res = await fetchReticulumInstanceSettings(window.api);
            if (res) {
                reticulumInstance = { ...reticulumInstance, ...res };
            }
        } catch (e) {
            console.error("Failed to load reticulum instance info", e);
        }
    }

    async function loadTelemetryPeers() {
        try {
            const response = await window.api.get("/api/v1/telemetry/peers");
            trustedTelemetryPeers = response.data?.peers || [];
        } catch (e) {
            console.error("Failed to load telemetry peers", e);
        }
    }

    async function updateConfigField(key: string, value: any) {
        if (key === "is_transport_enabled") {
            await onIsTransportEnabledChange(Boolean(value));
            return;
        }
        config[key] = value;
        try {
            const updated = await patchServerConfig({ [key]: value }, window.api);
            sanitizeColorConfigFields(updated);
            config = { ...config, ...updated };
            publishPatchedConfig(config);
        } catch (e) {
            console.error("Failed to update config field", key, e);
            ToastUtils.error(t("common.error"));
        }
    }

    async function onIsTransportEnabledChange(val: boolean) {
        config.is_transport_enabled = val;
        try {
            await applyTransportMode(val, window.api);
            ToastUtils.success(t("common.saved"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("common.error"));
        }
    }

    async function resetAppearanceDefaults() {
        const updated = await resetAppearanceDefaultsHelper(window.api);
        if (updated) {
            config = { ...config, ...updated };
        }
    }

    function onDetailedOutboundSendStatusChange(event: Event) {
        handleDetailedOutboundSendStatusChange((event.target as HTMLInputElement).checked);
    }

    function onOutboundTransferProgressEnabledChange(event: Event) {
        handleOutboundTransferProgressEnabledChange((event.target as HTMLInputElement).checked);
    }

    function onMessageTimestampGroupingChange(event: Event) {
        handleMessageTimestampGroupingChange((event.target as HTMLInputElement).checked);
    }

    function onVisualiserShowDisabledChange(val: boolean) {
        visualiserDisplayPrefs.showDisabledInterfaces = val;
        persistVisualiserShowDisabled(val);
    }

    function onVisualiserShowDiscoveredChange(val: boolean) {
        visualiserDisplayPrefs.showDiscoveredInterfaces = val;
        persistVisualiserShowDiscovered(val);
    }

    function onVisualiserRendererChange(val: string) {
        visualiserDisplayPrefs.renderer = normalizeVisualiserRenderer(val);
        persistVisualiserRenderer(val);
    }

    function onVisualiserViewModeChange(val: string) {
        visualiserDisplayPrefs.viewMode = normalizeVisualiserViewMode(val);
        persistVisualiserViewMode(val);
    }

    async function savePreferredPropagationNodeHash(showInvalidToast = false) {
        const updated = await savePreferredPropagationNodeHashHelper(config, showInvalidToast, window.api);
        if (updated) {
            config = { ...config, ...updated };
        }
    }

    async function flushArchivedPages() {
        await flushArchivedPagesHelper();
    }

    async function revokeTelemetryTrust(contact: any) {
        const ok = await revokeTelemetryTrustHelper(contact, window.api);
        if (ok) {
            trustedTelemetryPeers = trustedTelemetryPeers.filter((p) => p.id !== contact.id);
        }
    }

    async function onInboundStampsEnabledChange(value: boolean) {
        if (!value) {
            lastRememberedInboundStampCost = Number(config.lxmf_inbound_stamp_cost) || 8;
            await updateConfigField("lxmf_inbound_stamp_cost", 0);
        } else {
            await updateConfigField("lxmf_inbound_stamp_cost", lastRememberedInboundStampCost || 8);
        }
    }

    async function onLanguageChange(lang: string) {
        config.language = lang;
        await setLocale((window as any).__meshchatUiI18n, lang);
        await updateConfigField("language", lang);
    }

    async function updateReticulumInstance(patch: Record<string, any>) {
        reticulumInstanceSaving = true;
        try {
            const updated = await applyReticulumInstanceSettings(window.api, patch);
            if (updated) {
                reticulumInstance = { ...reticulumInstance, ...updated };
            }
            ToastUtils.success(t("common.saved"));
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.message || t("common.error"));
        } finally {
            reticulumInstanceSaving = false;
        }
    }

    async function saveRemoteManagementAllowed(allowed: string[]) {
        await updateReticulumInstance({ remote_management_allowed: allowed });
    }

    async function reloadRns() {
        reloadingRns = true;
        reloadRnsStatusMessage = t("app.reloading_rns");
        try {
            await window.api.post("/api/v1/reticulum/reload");
            reloadRnsStatusMessage = t("app.reload_rns_success");
            ToastUtils.success(t("app.reload_rns_success"));
        } catch (e: any) {
            reloadRnsStatusMessage = t("app.reload_rns_failed");
            ToastUtils.error(e?.response?.data?.message || t("app.reload_rns_failed"));
        } finally {
            reloadingRns = false;
        }
    }

    async function loadDesktopCloseSettings() {
        const settings = await fetchDesktopCloseSettings();
        if (settings) {
            desktopCloseSettings = settings;
        }
    }

    async function loadScreenSecuritySettings() {
        showWindowsScreenSecurity =
            typeof ElectronUtils.isWindowsElectron === "function" && ElectronUtils.isWindowsElectron();
        if (!showWindowsScreenSecurity) return;
        const res = await fetchScreenSecuritySettings();
        if (res != null) {
            screenSecurityEnabled = res;
        }
    }

    async function onScreenSecurityChange(value: boolean) {
        if (screenSecuritySaving) return;
        screenSecuritySaving = true;
        try {
            const res = await applyScreenSecurityChange(value);
            if (res != null) {
                screenSecurityEnabled = res;
            } else {
                screenSecurityEnabled = true;
            }
        } finally {
            screenSecuritySaving = false;
        }
    }

    async function onDesktopTrayEnabledChange(value: boolean) {
        const res = await applyDesktopTrayEnabledChange(value, desktopCloseSettings.closeBehavior);
        if (res) {
            desktopCloseSettings = res;
        }
    }

    async function onDesktopCloseBehaviorChange(value: string) {
        const res = await applyDesktopCloseBehaviorChange(value, desktopCloseSettings.trayEnabled !== false);
        if (res) {
            desktopCloseSettings = res;
        }
    }

    function onSelectTab(tabId: string) {
        if (isSearching) {
            if (searchTabFilter === tabId) {
                searchTabFilter = null;
            } else {
                searchTabFilter = tabId;
            }
            return;
        }
        activeSettingsTab = normalizeSettingsTabId(tabId);
        searchQuery = "";
        searchTabFilter = null;
    }

    function onFilterTab(tabId: string | null) {
        searchTabFilter = tabId;
    }

    function onClearSearch() {
        searchQuery = "";
        searchTabFilter = null;
    }

    async function onMicronWasmOverrideSaved() {
        const label = await getEffectiveMicronWasmReleaseLabel();
        if (typeof label === "string") {
            micronReleaseLabel = label;
        }
        isWasmBundled = isMicronWasmBundled();
    }

    let searchInputEl: HTMLInputElement | undefined = $state();

    function onKeydown(e: KeyboardEvent) {
        if (
            e.key === "/" &&
            document.activeElement !== searchInputEl &&
            !["INPUT", "TEXTAREA", "SELECT"].includes((document.activeElement as HTMLElement)?.tagName)
        ) {
            e.preventDefault();
            searchInputEl?.focus();
        }
    }

    onMount(() => {
        loadConfig();
        loadServerSecurity();
        loadReticulumInstance();
        loadTelemetryPeers();
        loadDesktopCloseSettings();
        loadScreenSecuritySettings();
        isWasmBundled = isMicronWasmBundled();
        void getEffectiveMicronWasmReleaseLabel().then((label) => {
            if (typeof label === "string") micronReleaseLabel = label;
        });

        window.addEventListener("keydown", onKeydown);

        GlobalEmitter.on("identity-switched", loadConfig);
        GlobalEmitter.on("identity-switched-apply", loadConfig);

        return () => {
            window.removeEventListener("keydown", onKeydown);
            GlobalEmitter.off("identity-switched", loadConfig);
            GlobalEmitter.off("identity-switched-apply", loadConfig);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas text-sem-fg">
    <div
        class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
    >
        <div class="space-y-6 w-full max-w-5xl mx-auto min-w-0">
            <!-- Header & Search -->
            <div
                class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-sem-border pb-4"
            >
                <div>
                    <h1 class="text-2xl font-black text-sem-fg tracking-tight">{t("settings.title")}</h1>
                    <p class="text-sm text-sem-fg-muted">{t("settings.description")}</p>
                </div>
                <div class="relative min-w-[16rem]">
                    <input
                        bind:this={searchInputEl}
                        bind:value={searchQuery}
                        type="search"
                        placeholder={t("settings.search_placeholder")}
                        class="input-field pl-9 pr-8 w-full"
                    />
                    <MaterialDesignIcon
                        iconName="magnify"
                        class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-sem-fg-muted pointer-events-none"
                    />
                    {#if searchQuery}
                        <button
                            type="button"
                            class="absolute right-2.5 top-1/2 -translate-y-1/2 text-sem-fg-muted hover:text-sem-fg cursor-pointer"
                            onclick={onClearSearch}
                        >
                            <MaterialDesignIcon iconName="close" class="size-4" />
                        </button>
                    {/if}
                </div>
            </div>

            <!-- Settings Navigation + Sections -->
            <div class="settings-panel">
                <SettingsNav
                    activeTab={activeSettingsTab}
                    {matchCounts}
                    {isSearching}
                    onselecttab={onSelectTab}
                />

                <div class="settings-panel__content">
                    {#if !hasSearchResults}
                        <div class="py-12 text-center text-sem-fg-muted">
                            <MaterialDesignIcon
                                iconName="magnify-remove-outline"
                                class="size-12 mx-auto mb-3 opacity-40"
                            />
                            <h3 class="text-lg font-semibold text-sem-fg">{t("settings.search_no_results")}</h3>
                            <p class="mt-1 text-sm">{t("settings.search_no_match", { query: searchQuery })}</p>
                            <button type="button" class="primary-chip mt-4 cursor-pointer" onclick={onClearSearch}>
                                {t("settings.clear_search")}
                            </button>
                        </div>
                    {:else}
                        <div class="space-y-0">
                            <!-- General tab sections -->
                            <LanguageSettingsSection
                                visible={showSection("language")}
                                language={config.language}
                                onchange={onLanguageChange}
                            />
                            <AppearanceSettingsSection
                                visible={showSection("appearance")}
                                {config}
                                detailedOutboundSendStatus={GlobalState.detailedOutboundSendStatus}
                                outboundTransferProgressEnabled={GlobalState.outboundTransferProgressEnabled}
                                messageTimestampGroupingEnabled={GlobalState.messageTimestampGroupingEnabled}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                                onresetappearancedefaults={resetAppearanceDefaults}
                                ondetailedoutboundsendstatuschange={onDetailedOutboundSendStatusChange}
                                onoutboundtransferprogressenabledchange={onOutboundTransferProgressEnabledChange}
                                onmessagetimestampgroupingchange={onMessageTimestampGroupingChange}
                            />
                            <BatterySettingsSection visible={showSection("battery")} />
                            <ExperimentalLiveSettingsSection
                                visible={showSection("experimentalLive")}
                                liveTransportMode={config.live_transport_mode}
                                sidecarEnabled={Boolean(config.webtransport_sidecar_enabled)}
                                onmodechange={(val) => updateConfigField("live_transport_mode", val)}
                                onsidecarchange={(val) => updateConfigField("webtransport_sidecar_enabled", val)}
                            />
                            <DesktopSettingsSection
                                visible={showSection("desktop")}
                                {config}
                                {desktopCloseSettings}
                                onhardwareaccelerationchange={(val) =>
                                    updateConfigField("desktop_hardware_acceleration_enabled", val)}
                                ontrayenabledchange={onDesktopTrayEnabledChange}
                                onclosebehaviorchange={onDesktopCloseBehaviorChange}
                            />
                            <AndroidSettingsSection visible={showSection("android")} />
                            <ShortcutsSettingsSection visible={showSection("shortcuts")} />
                            <LocationSettingsSection
                                visible={showSection("location")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />

                            <!-- Messages tab sections -->
                            <StrangerProtectionSettingsSection
                                visible={showSection("strangerProtection")}
                                {config}
                                onblockattachmentschange={(val) =>
                                    updateConfigField("block_attachments_from_strangers", val)}
                                onblockallchange={(val) => updateConfigField("block_all_from_strangers", val)}
                                onunknownbannerchange={(val) => updateConfigField("show_unknown_contact_banner", val)}
                                onwarnlinkschange={(val) => updateConfigField("warn_on_stranger_links", val)}
                            />
                            <MessagesSettingsSection
                                visible={showSection("messages")}
                                {config}
                                {inboundStampsEnabled}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                                oninboundstampschange={onInboundStampsEnabledChange}
                            />
                            <NotificationSoundSettings
                                showSection={showSection("notificationSounds")}
                                {config}
                                updateConfig={(patch) =>
                                    Object.entries(patch).forEach(([k, v]) => updateConfigField(k, v))}
                            />
                            <PropagationSettingsSection
                                visible={showSection("propagation")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                                onsavepreferredhash={savePreferredPropagationNodeHash}
                                onclearpreferredhash={() => {
                                    config.lxmf_preferred_propagation_node_destination_hash = "";
                                    savePreferredPropagationNodeHash(true);
                                }}
                            />
                            <StickersSettingsSection visible={showSection("stickers")} />
                            <GifsSettingsSection visible={showSection("gifs")} />

                            <!-- Network tab sections -->
                            <TransportSettingsSection
                                visible={showSection("transport")}
                                {config}
                                bind:reticulumInstance
                                {reticulumInstanceSaving}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                                onupdatereticuluminstance={updateReticulumInstance}
                                onsaveremotemanagementallowed={saveRemoteManagementAllowed}
                            />
                            <InterfacesSettingsSection
                                visible={showSection("interfaces")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />
                            <VisualiserSettingsSection
                                visible={showSection("visualiser")}
                                renderer={visualiserDisplayPrefs.renderer}
                                viewMode={visualiserDisplayPrefs.viewMode}
                                showDisabledInterfaces={visualiserDisplayPrefs.showDisabledInterfaces}
                                showDiscoveredInterfaces={visualiserDisplayPrefs.showDiscoveredInterfaces}
                                onrendererchange={onVisualiserRendererChange}
                                onviewmodechange={onVisualiserViewModeChange}
                                onshowdisabledchange={onVisualiserShowDisabledChange}
                                onshowdiscoveredchange={onVisualiserShowDiscoveredChange}
                            />
                            <CrawlerSettingsSection
                                visible={showSection("crawler")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />
                            <NetworkSecuritySettingsSection
                                visible={showSection("networkSecurity")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />
                            <TelephonySettingsSection
                                visible={showSection("telephony")}
                                {config}
                                onenabledchange={(val) => updateConfigField("telephone_enabled", val)}
                            />

                            <!-- Nomad tab sections -->
                            <ArchiverSettingsSection
                                visible={showSection("archiver")}
                                {config}
                                onenabledchange={(val) => updateConfigField("page_archiver_enabled", val)}
                                onconfigchange={(patch) =>
                                    Object.entries(patch).forEach(([k, v]) => updateConfigField(k, v))}
                                onflush={flushArchivedPages}
                            />
                            <NomadRendererSettingsSection
                                visible={showSection("nomadRenderer")}
                                {config}
                                micronWasmBundledInBuild={isWasmBundled}
                                micronWasmReleaseLabel={micronReleaseLabel}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                                onopenmicronwasmmodal={() => (micronWasmUpdateModalOpen = true)}
                            />

                            <!-- Privacy tab sections -->
                            <PrivacyDataSettingsSection
                                visible={showSection("privacyData")}
                                {config}
                                {reticulumInstance}
                                {reticulumInstanceSaving}
                                {showWindowsScreenSecurity}
                                bind:screenSecurityEnabled
                                {screenSecuritySaving}
                                {trustedTelemetryPeers}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                                onupdatereticuluminstance={updateReticulumInstance}
                                onscreensecuritychange={onScreenSecurityChange}
                                onrevoketelemetrypeer={revokeTelemetryTrust}
                            />
                            <BlockedSettingsSection visible={showSection("blocked")} />
                            <BanishmentSettingsSection
                                visible={showSection("banishment")}
                                {config}
                                onenabledchange={(val) => updateConfigField("banished_effect_enabled", val)}
                                ontextchange={(val) => updateConfigField("banished_text", val)}
                                oncolorchange={(val) => updateConfigField("banished_color", val)}
                            />
                            <AuthSettingsSection
                                visible={showSection("auth")}
                                {config}
                                onauthenabledchange={(val) => updateConfigField("auth_enabled", val)}
                            />
                            <WebExposureSettingsSection
                                visible={showSection("webExposure")}
                                {serverSecurity}
                                {exposureAckFirewall}
                                {exposureAckVpn}
                                onackfirewallchange={(val) => (exposureAckFirewall = val)}
                                onackvpnchange={(val) => (exposureAckVpn = val)}
                                onallowlistchange={(val) => {
                                    serverSecurity.web_ui_ip_allowlist = val;
                                    updateConfigField("web_ui_ip_allowlist", val);
                                }}
                            />
                            <CspSettingsSection
                                visible={showSection("csp")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />

                            <!-- Maintenance tab sections -->
                            <MaintenanceSettingsSection
                                visible={showSection("maintenance")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />
                            <SelftestSettingsSection visible={showSection("selftest")} />
                            <InfrastructureSettingsSection
                                visible={showSection("infrastructure")}
                                {config}
                                onupdatefield={(d) => updateConfigField(d.key, d.value)}
                            />
                            <ReticulumStackSettingsSection
                                visible={showSection("maintenance")}
                                {reloadingRns}
                                {reloadRnsStatusMessage}
                                onreloadrns={reloadRns}
                            />

                            <!-- Plugins tab sections -->
                            <PluginsSettingsSection visible={showSection("plugins")} />
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <MicronWasmUpdateModal bind:open={micronWasmUpdateModalOpen} onsaved={onMicronWasmOverrideSaved} />
</div>

<style>
    .settings-panel {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    @media (min-width: 1024px) {
        .settings-panel {
            flex-direction: row;
            align-items: flex-start;
            gap: 2rem;
        }
    }
    .settings-panel__content {
        flex: 1 1 0%;
        min-width: 0;
        display: flex;
        flex-direction: column;
    }
    :global(.settings-section) {
        width: 100%;
        border-bottom: 1px solid var(--mc-border);
        padding: 1.5rem 0;
        display: flex;
        flex-direction: column;
        break-inside: avoid;
    }
    @media (min-width: 640px) {
        :global(.settings-section) {
            padding: 2rem 0;
        }
    }
    :global(.settings-section__header) {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--mc-border);
    }
    :global(.settings-section__header h2) {
        font-size: 1.125rem;
        line-height: 1.75rem;
        font-weight: 600;
        color: var(--mc-text);
    }
    :global(.settings-section__header p) {
        font-size: 0.875rem;
        line-height: 1.25rem;
        color: var(--mc-text-muted);
    }
    :global(.settings-section__eyebrow) {
        font-size: 0.75rem;
        line-height: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--mc-text-muted);
    }
    :global(.settings-section__body) {
        padding-top: 1rem;
        color: var(--mc-text);
    }
    .settings-panel__content :global(.settings-section:first-child) {
        padding-top: 0;
    }
    .settings-panel__content :global(.settings-section:last-child) {
        border-bottom-width: 0;
    }
</style>
