<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalState from "../../js/GlobalState.js";
    import { t } from "../../js/i18n.js";
    import { INTERFACES_ROUTE_PATH } from "./lib/constants.js";
    import type {
        DiscoveryFields,
        InterfaceModule,
        KernelInterface,
        Comport,
        CommunityInterface,
        ConfiguredInterface,
        RNodeLoRaParameters,
        ReticulumDiscovery,
        SharedInterfaceSettings,
    } from "./lib/types.js";
    import {
        fetchInterfaces,
        fetchInterfaceToEdit,
        fetchDiscoveryConfigApi,
        saveDiscoveryConfigApi,
        fetchComportsApi,
        fetchKernelInterfacesApi,
        fetchCommunityInterfacesApi,
        fetchInterfaceModulesApi,
        uploadInterfaceModuleApi,
        deleteInterfaceModuleApi,
        saveInterfaceApi,
    } from "./lib/interfacesApi.js";
    import { parseBool } from "./lib/interfacesFormat.js";
    import {
        calculateLoRaParameters,
        parseRawConfig,
        buildPayloadFromImportedConfig,
    } from "./lib/addInterfaceState.js";
    import { buildSavePayload } from "./lib/addInterfacePayload.js";

    import AddInterfaceHeader from "./components/AddInterfaceHeader.svelte";
    import AddInterfaceFooter from "./components/AddInterfaceFooter.svelte";
    import AddInterfaceTypeSelector from "./components/AddInterfaceTypeSelector.svelte";
    import AddInterfaceConnectionDetails from "./components/AddInterfaceConnectionDetails.svelte";
    import AddInterfaceAdvancedPanel from "./components/AddInterfaceAdvancedPanel.svelte";
    import AddInterfaceDiscoveryPanel from "./components/AddInterfaceDiscoveryPanel.svelte";
    import AddInterfaceSidebar from "./components/AddInterfaceSidebar.svelte";

    interface Props {
        interfaceName?: string;
        routeQuery?: Record<string, string>;
    }

    let { interfaceName = "", routeQuery = {} }: Props = $props();

    const editInterfaceName = $derived(
        interfaceName || (typeof routeQuery.interface_name === "string" ? routeQuery.interface_name : "")
    );
    const isEditingInterface = $derived(Boolean(editInterfaceName));

    let isSaving = $state(false);
    let savingDiscovery = $state(false);

    let newInterfaceName = $state("");
    let newInterfaceType = $state<string | null>(null);

    let customIsBusy = $state(false);
    let modulesPath = $state("");
    let installedModules = $state<InterfaceModule[]>([]);

    let form = $state({
        targetHost: null as string | null,
        targetPort: null as number | string | null,
        transportIdentity: null as string | null,
        kissFraming: false,
        i2pTunneled: false,
        bootstrapOnly: true,
        connectTimeout: null as number | string | null,
        maxReconnectTries: null as number | string | null,
        fixedMtu: null as number | string | null,
        backboneListenMode: false,
        listenIp: null as string | null,
        listenPort: null as number | string | null,
        listenDevice: null as string | null,
        preferIPv6: true,
        blockFastFlapping: true,
        fastFlappingBlockTime: 720 as number | string | null,
        fastFlappingThreshold: 20 as number | string | null,
        fastFlappingGrace: 5 as number | string | null,
        forwardIp: null as string | null,
        forwardPort: null as number | string | null,
        udpDevice: null as string | null,
        i2pConnectable: false,
        i2pPeers: [] as string[],
        rnodeTransport: "serial" as "serial" | "tcp" | "bluetooth" | "ble",
        rnodePort: null as string | null,
        rnodeTcpHost: null as string | null,
        rnodeTcpPort: null as number | string | null,
        rnodeFrequency: null as number | string | null,
        rnodeBandwidth: 125000 as number | string | null,
        rnodeSpreadingFactor: 7 as number | string | null,
        rnodeCodingRate: 5 as number | string | null,
        rnodeTxpower: 17 as number | string | null,
        rnodeFlowControl: false,
        rnodeAutotune: false,
        rnodeIdCallsign: null as string | null,
        rnodeIdInterval: null as number | string | null,
        rnodeAirtimeLimitLong: null as number | string | null,
        rnodeAirtimeLimitShort: null as number | string | null,
        serialSpeed: 115200 as number | string | null,
        serialDatabits: 8 as number | string | null,
        serialParity: "none" as string | null,
        serialStopbits: 1 as number | string | null,
        ax25Callsign: null as string | null,
        ax25Ssid: 0 as number | string | null,
        kissPreamble: null as number | string | null,
        kissTxtail: null as number | string | null,
        kissPersistence: null as number | string | null,
        kissSlottime: null as number | string | null,
        kissFlowControl: undefined as boolean | undefined,
        kissIdCallsign: null as string | null,
        kissIdInterval: null as number | string | null,
        autoGroupId: null as string | null,
        autoMulticastType: "link" as string | null,
        autoDevices: null as string | null,
        autoIgnoredDevices: null as string | null,
        autoDiscoveryScope: null as string | null,
        autoDiscoveryPort: null as number | string | null,
        autoDataPort: null as number | string | null,
        autoConfiguredBitrate: null as number | string | null,
        httpMode: "client" as "client" | "server",
        httpServerUrl: null as string | null,
        httpPollInterval: 0.1 as number | string | null,
        httpListenHost: "0.0.0.0" as string | null,
        httpListenPort: 8080 as number | string | null,
        httpMtu: 4096 as number | string | null,
        httpVersion: 1 as number | string | null,
        httpUserAgent: "RNS-HTTP-Tunnel/1.0" as string | null,
        httpCheckUserAgent: true,
        httpTlsVerify: true,
        httpTlsCertfile: null as string | null,
        httpTlsKeyfile: null as string | null,
        customTypeName: "",
        customOptionsJson: "{}",
        customOverwrite: false,
    });

    let sharedSettings = $state<SharedInterfaceSettings>({
        mode: null,
        network_name: null,
        passphrase: null,
        ifac_size: null,
        bitrate: null,
        recursive_prs: false,
        announces_from_internal: true,
        announces_to_internal: false,
        gravity: null,
    });

    let discovery = $state<DiscoveryFields>({
        discoverable: false,
        discovery_name: null,
        announce_interval: null,
        reachable_on: null,
        latitude: null,
        longitude: null,
        height: null,
        location_cmd: null,
        discovery_stamp_value: 1,
        discovery_encrypt: true,
        publish_ifac: false,
    });

    let reticulumDiscovery = $state<ReticulumDiscovery>({
        discover_interfaces: false,
        default_bootstrap_only: false,
        interface_discovery_whitelist: "",
        interface_discovery_blacklist: "",
    });

    let loraBase = $state({
        antennaGain: 0,
        noiseFloor: -120,
    });

    const loraCalculations = $derived.by(() => {
        if (newInterfaceType === "RNodeInterface" || newInterfaceType === "RNodeIPInterface") {
            return calculateLoRaParameters(
                Number(form.rnodeBandwidth) || 125000,
                Number(form.rnodeSpreadingFactor) || 7,
                Number(form.rnodeCodingRate) || 5,
                loraBase.noiseFloor ?? -120,
                loraBase.antennaGain ?? 0,
                Number(form.rnodeTxpower) || 17
            );
        }
        return { sensitivity: null, dataRate: null, linkBudget: null };
    });

    const loraParams = $derived<RNodeLoRaParameters>({
        antennaGain: loraBase.antennaGain ?? 0,
        noiseFloor: loraBase.noiseFloor ?? -120,
        sensitivity: loraCalculations.sensitivity ?? null,
        dataRate: loraCalculations.dataRate ?? null,
        linkBudget: loraCalculations.linkBudget ?? null,
    });

    let comports = $state<Comport[]>([]);
    let comportsLoading = $state(false);
    let hostKernelInterfaces = $state<KernelInterface[]>([]);
    let hostKernelInterfacesLoading = $state(false);
    let communityInterfaces = $state<CommunityInterface[]>([]);
    let communityFetchDone = $state(false);
    let showCommunityPresets = $state(true);
    let existingInterfaces = $state<Record<string, ConfiguredInterface>>({});

    const hasExistingI2PInterface = $derived(
        Object.values(existingInterfaces || {}).some((iface) => iface && iface.type === "I2PInterface")
    );
    const transportEnabled = $derived(Boolean((GlobalState as any).config?.is_transport_enabled));
    const canAddI2PInterface = $derived(
        (isEditingInterface && newInterfaceType === "I2PInterface") || (transportEnabled && !hasExistingI2PInterface)
    );

    onMount(() => {
        loadInitialData();
    });

    async function loadInitialData() {
        try {
            const ifacesRes = await fetchInterfaces();
            existingInterfaces = ifacesRes.interfaces || {};
        } catch {
            /* ignore */
        }

        refreshComports();
        loadKernelInterfaces();
        loadCommunityInterfaces();
        loadDiscoveryConfig();
        loadInstalledModules();

        if (editInterfaceName) {
            loadInterfaceToEdit(editInterfaceName);
        } else if (routeQuery) {
            applyQueryPrefills();
            if (routeQuery.from_discovered === "1") {
                applyDiscoveredInterfacePrefill();
            }
        }
    }

    async function refreshComports() {
        comportsLoading = true;
        try {
            comports = await fetchComportsApi();
        } catch {
            /* ignore */
        } finally {
            comportsLoading = false;
        }
    }

    async function loadKernelInterfaces() {
        hostKernelInterfacesLoading = true;
        try {
            const res = await fetchKernelInterfacesApi();
            hostKernelInterfaces = res.interfaces || [];
        } catch {
            /* ignore */
        } finally {
            hostKernelInterfacesLoading = false;
        }
    }

    async function loadCommunityInterfaces() {
        try {
            communityInterfaces = await fetchCommunityInterfacesApi();
        } catch {
            /* ignore */
        } finally {
            communityFetchDone = true;
        }
    }

    async function loadDiscoveryConfig() {
        try {
            const cfg = await fetchDiscoveryConfigApi();
            reticulumDiscovery.discover_interfaces = Boolean(cfg.discover_interfaces);
            reticulumDiscovery.default_bootstrap_only = Boolean(cfg.default_bootstrap_only);
            reticulumDiscovery.interface_discovery_whitelist = cfg.interface_discovery_whitelist || "";
            reticulumDiscovery.interface_discovery_blacklist = cfg.interface_discovery_blacklist || "";
        } catch {
            /* ignore */
        }
    }

    async function loadInstalledModules() {
        try {
            const res = await fetchInterfaceModulesApi();
            installedModules = res.modules || [];
            modulesPath = res.interface_path || "";
        } catch {
            /* ignore */
        }
    }

    async function loadInterfaceToEdit(name: string) {
        try {
            const iface = await fetchInterfaceToEdit(name);
            newInterfaceName = name;
            applyConfig(iface);
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to load interface for editing");
        }
    }

    function applyQueryPrefills() {
        if (routeQuery.type) newInterfaceType = routeQuery.type;
        if (routeQuery.target_host) form.targetHost = routeQuery.target_host;
        if (routeQuery.target_port) form.targetPort = routeQuery.target_port;
        if (routeQuery.name) newInterfaceName = routeQuery.name;
    }

    function applyConfig(cfg: Record<string, any>) {
        if (cfg.name) newInterfaceName = cfg.name;
        if (cfg.type) newInterfaceType = cfg.type;
        if (cfg.target_host) form.targetHost = cfg.target_host;
        if (cfg.remote) form.targetHost = cfg.remote;
        if (cfg.target_port !== undefined && cfg.target_port !== null) form.targetPort = cfg.target_port;
        if (cfg.transport_identity) form.transportIdentity = cfg.transport_identity;
        if (cfg.kiss_framing !== undefined) form.kissFraming = parseBool(cfg.kiss_framing);
        if (cfg.i2p_tunneled !== undefined) form.i2pTunneled = parseBool(cfg.i2p_tunneled);
        if (cfg.connect_timeout !== undefined) form.connectTimeout = cfg.connect_timeout;
        if (cfg.max_reconnect_tries !== undefined) form.maxReconnectTries = cfg.max_reconnect_tries;
        if (cfg.fixed_mtu !== undefined) form.fixedMtu = cfg.fixed_mtu;
        if (cfg.listen_ip) form.listenIp = cfg.listen_ip;
        if (cfg.listen_port !== undefined && cfg.listen_port !== null) form.listenPort = cfg.listen_port;
        if (cfg.forward_ip) form.forwardIp = cfg.forward_ip;
        if (cfg.forward_port !== undefined && cfg.forward_port !== null) form.forwardPort = cfg.forward_port;
        if (cfg.device) {
            form.udpDevice = cfg.device;
            form.listenDevice = cfg.device;
        }
        if (cfg.prefer_ipv6 !== undefined) form.preferIPv6 = parseBool(cfg.prefer_ipv6);
        if (cfg.connectable !== undefined) form.i2pConnectable = parseBool(cfg.connectable);
        if (cfg.peers) form.i2pPeers = Array.isArray(cfg.peers) ? cfg.peers : [cfg.peers];
        else if (cfg.i2p_peers) form.i2pPeers = Array.isArray(cfg.i2p_peers) ? cfg.i2p_peers : [cfg.i2p_peers];
        if (cfg.port) form.rnodePort = cfg.port;
        if (cfg.frequency !== undefined) form.rnodeFrequency = cfg.frequency;
        if (cfg.bandwidth !== undefined) form.rnodeBandwidth = cfg.bandwidth;
        if (cfg.spreadingfactor !== undefined) form.rnodeSpreadingFactor = cfg.spreadingfactor;
        if (cfg.codingrate !== undefined) form.rnodeCodingRate = cfg.codingrate;
        if (cfg.txpower !== undefined) form.rnodeTxpower = cfg.txpower;
        if (cfg.flow_control !== undefined) {
            form.rnodeFlowControl = parseBool(cfg.flow_control);
            form.kissFlowControl = parseBool(cfg.flow_control);
        }
        if (cfg.autotune !== undefined) form.rnodeAutotune = parseBool(cfg.autotune);
        if (cfg.id_callsign) {
            form.rnodeIdCallsign = cfg.id_callsign;
            form.kissIdCallsign = cfg.id_callsign;
        }
        if (cfg.id_interval !== undefined) {
            form.rnodeIdInterval = cfg.id_interval;
            form.kissIdInterval = cfg.id_interval;
        }
        if (cfg.airtime_limit_long !== undefined) form.rnodeAirtimeLimitLong = cfg.airtime_limit_long;
        if (cfg.airtime_limit_short !== undefined) form.rnodeAirtimeLimitShort = cfg.airtime_limit_short;
        if (cfg.speed !== undefined) form.serialSpeed = cfg.speed;
        if (cfg.databits !== undefined) form.serialDatabits = cfg.databits;
        if (cfg.parity !== undefined) form.serialParity = cfg.parity;
        if (cfg.stopbits !== undefined) form.serialStopbits = cfg.stopbits;
        if (cfg.preamble !== undefined) form.kissPreamble = cfg.preamble;
        if (cfg.txtail !== undefined) form.kissTxtail = cfg.txtail;
        if (cfg.persistence !== undefined) form.kissPersistence = cfg.persistence;
        if (cfg.slottime !== undefined) form.kissSlottime = cfg.slottime;
        if (cfg.callsign) form.ax25Callsign = cfg.callsign;
        if (cfg.ssid !== undefined) form.ax25Ssid = cfg.ssid;
        if (cfg.group_id) form.autoGroupId = cfg.group_id;
        if (cfg.multicast_address_type) form.autoMulticastType = cfg.multicast_address_type;
        if (cfg.devices) form.autoDevices = cfg.devices;
        if (cfg.ignored_devices) form.autoIgnoredDevices = cfg.ignored_devices;
        if (cfg.discovery_scope) form.autoDiscoveryScope = cfg.discovery_scope;
        if (cfg.discovery_port !== undefined) form.autoDiscoveryPort = cfg.discovery_port;
        if (cfg.data_port !== undefined) form.autoDataPort = cfg.data_port;
        if (cfg.configured_bitrate !== undefined) form.autoConfiguredBitrate = cfg.configured_bitrate;
        if (cfg.mode) {
            sharedSettings.mode = cfg.mode;
            form.httpMode = cfg.mode === "server" ? "server" : "client";
        }
        if (cfg.server_url) form.httpServerUrl = cfg.server_url;
        if (cfg.poll_interval !== undefined) form.httpPollInterval = cfg.poll_interval;
        if (cfg.mtu !== undefined) form.httpMtu = cfg.mtu;
        if (cfg.http_version !== undefined) form.httpVersion = cfg.http_version;
        if (cfg.user_agent) form.httpUserAgent = cfg.user_agent;
        if (cfg.network_name) sharedSettings.network_name = cfg.network_name;
        if (cfg.passphrase) sharedSettings.passphrase = cfg.passphrase;
        if (cfg.bitrate !== undefined) sharedSettings.bitrate = cfg.bitrate;
        if (cfg.recursive_prs !== undefined) sharedSettings.recursive_prs = parseBool(cfg.recursive_prs);
        if (cfg.announces_from_internal !== undefined)
            sharedSettings.announces_from_internal = parseBool(cfg.announces_from_internal);
        if (cfg.announces_to_internal !== undefined)
            sharedSettings.announces_to_internal = parseBool(cfg.announces_to_internal);
        if (cfg.gravity !== undefined) sharedSettings.gravity = cfg.gravity;
        if (cfg.bootstrap_only !== undefined) form.bootstrapOnly = parseBool(cfg.bootstrap_only);
        if (cfg.discoverable !== undefined) discovery.discoverable = parseBool(cfg.discoverable);
        if (cfg.discovery_name) discovery.discovery_name = cfg.discovery_name;
        if (cfg.announce_interval !== undefined && cfg.announce_interval !== null)
            discovery.announce_interval = Number(cfg.announce_interval);
        if (cfg.reachable_on) discovery.reachable_on = cfg.reachable_on;
        if (cfg.latitude !== undefined && cfg.latitude !== null) discovery.latitude = Number(cfg.latitude);
        if (cfg.longitude !== undefined && cfg.longitude !== null) discovery.longitude = Number(cfg.longitude);
        if (cfg.height !== undefined && cfg.height !== null) discovery.height = Number(cfg.height);
        if (cfg.location_cmd) discovery.location_cmd = cfg.location_cmd;
        if (cfg.discovery_stamp_value !== undefined && cfg.discovery_stamp_value !== null)
            discovery.discovery_stamp_value = Number(cfg.discovery_stamp_value);
        if (cfg.discovery_encrypt !== undefined) discovery.discovery_encrypt = parseBool(cfg.discovery_encrypt);
        if (cfg.publish_ifac !== undefined) discovery.publish_ifac = parseBool(cfg.publish_ifac);
    }

    async function applyDiscoveredInterfacePrefill() {
        let prefill: any = null;
        try {
            if (typeof sessionStorage !== "undefined") {
                const raw = sessionStorage.getItem("meshchatx.discoveredInterfacePrefill");
                if (raw) {
                    prefill = JSON.parse(raw);
                    sessionStorage.removeItem("meshchatx.discoveredInterfacePrefill");
                }
            }
        } catch {
            /* ignore */
        }
        if (!prefill) return;

        if (prefill.config_entry) {
            const configs = parseRawConfig(prefill.config_entry);
            if (configs.length > 0) {
                await quickAddInterfaceFromConfig(configs[0]);
                return;
            }
        }

        const config = {
            name: prefill.name || "Discovered Interface",
            type: prefill.type || "BackboneInterface",
            target_host: prefill.target_host || null,
            target_port: prefill.target_port != null ? String(prefill.target_port) : null,
            transport_identity: prefill.transport_identity || null,
            network_name: prefill.network_name || null,
            passphrase: prefill.passphrase || null,
            frequency: prefill.frequency ?? null,
            bandwidth: prefill.bandwidth ?? null,
            spreadingfactor: prefill.spreadingfactor ?? null,
            codingrate: prefill.codingrate ?? null,
            latitude: prefill.latitude ?? null,
            longitude: prefill.longitude ?? null,
            height: prefill.height ?? null,
        };
        applyConfig(config);
        ToastUtils.success("Discovered interface settings prefilled");
    }

    async function quickAddInterfaceFromConfig(config: Record<string, any>) {
        if (!config || !config.type || !config.name || isSaving) {
            return;
        }
        if (config.type === "I2PInterface") {
            ToastUtils.error("I2P interface import not supported via discovered prefill");
            return;
        }
        isSaving = true;
        try {
            const payload = buildPayloadFromImportedConfig(config);
            await window.api.post("/api/v1/reticulum/interfaces/add", payload);
            ToastUtils.showSuccess(`Imported interface "${config.name}"`);
            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.add(config.name);
            navigateBack();
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to import interface");
        } finally {
            isSaving = false;
        }
    }

    async function handleSave() {
        if (!newInterfaceName.trim()) {
            DialogUtils.alert("Interface name is required");
            return;
        }
        if (!newInterfaceType) {
            DialogUtils.alert("Please select a transport type");
            return;
        }

        if (form.fixedMtu != null && Number(form.fixedMtu) < 500) {
            ToastUtils.error("Fixed MTU must be at least 500 bytes");
            return;
        }

        if (
            newInterfaceType === "HTTPInterface" &&
            form.httpMode === "client" &&
            (!form.httpServerUrl || !form.httpServerUrl.trim())
        ) {
            ToastUtils.error("Server URL is required");
            return;
        }

        if (newInterfaceType === "I2PInterface" && !canAddI2PInterface) {
            ToastUtils.error(
                !transportEnabled ? t("interfaces.i2p_transport_required") : t("interfaces.i2p_already_exists")
            );
            return;
        }

        if (newInterfaceType === "I2PInterface") {
            const validPeers = form.i2pPeers.map((p) => String(p).trim()).filter(Boolean);
            if (validPeers.length === 0) {
                ToastUtils.error("I2P peers list cannot be empty");
                return;
            }
        }

        isSaving = true;
        try {
            let payload: Record<string, any>;
            try {
                payload = buildSavePayload(newInterfaceType, sharedSettings, form, discovery);
            } catch (err: any) {
                ToastUtils.error(err?.message || "Invalid interface configuration");
                return;
            }

            await saveInterfaceApi(newInterfaceName.trim(), payload, isEditingInterface);

            if (isEditingInterface) {
                ToastUtils.showSuccess(`Saved interface "${newInterfaceName.trim()}"`);
            } else {
                ToastUtils.showSuccess(`Created interface "${newInterfaceName.trim()}"`);
            }

            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.add(newInterfaceName.trim());
            navigateBack();
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to save interface");
        } finally {
            isSaving = false;
        }
    }

    async function handleSaveDiscoveryPrefs() {
        savingDiscovery = true;
        try {
            await saveDiscoveryConfigApi(reticulumDiscovery);
            ToastUtils.showSuccess("Discovery listener preferences saved");
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to save discovery preferences");
        } finally {
            savingDiscovery = false;
        }
    }

    async function handleUploadModule(file: File) {
        customIsBusy = true;
        try {
            await uploadInterfaceModuleApi(file, form.customOverwrite);
            ToastUtils.showSuccess(`Installed interface module ${file.name}`);
            await loadInstalledModules();
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to upload module");
        } finally {
            customIsBusy = false;
        }
    }

    async function handleDeleteModule(typeName: string) {
        if (!confirm(`Delete custom interface module ${typeName}?`)) return;
        try {
            await deleteInterfaceModuleApi(typeName);
            ToastUtils.showSuccess(`Deleted module ${typeName}`);
            await loadInstalledModules();
        } catch (err: any) {
            ToastUtils.showError(err?.message || "Failed to delete module");
        }
    }

    function navigateBack() {
        window.location.hash = `#${INTERFACES_ROUTE_PATH}`;
    }
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <div class="overflow-y-auto flex-1 min-h-0">
        <div class="w-full max-w-[1920px] mx-auto px-4 md:px-5 lg:px-8 py-4 md:py-6 lg:py-8 space-y-6">
            <AddInterfaceHeader isEditing={isEditingInterface} onback={navigateBack} />

            <div class="flex flex-col-reverse gap-8 xl:flex-row xl:items-start xl:gap-10">
                <div class="flex-1 min-w-0 space-y-6 xl:max-w-4xl 2xl:max-w-5xl">
                    <!-- Main Form Card -->
                    <div class="glass-card space-y-8">
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <!-- Basic Configuration Column -->
                            <AddInterfaceTypeSelector
                                name={newInterfaceName}
                                type={newInterfaceType}
                                isEditing={isEditingInterface}
                                onnamechange={(v) => (newInterfaceName = v)}
                                ontypechange={(v) => (newInterfaceType = v)}
                            />

                            <!-- Connection Details Column -->
                            <AddInterfaceConnectionDetails
                                interfaceType={newInterfaceType}
                                {form}
                                {comports}
                                {comportsLoading}
                                {hostKernelInterfaces}
                                {hostKernelInterfacesLoading}
                                {installedModules}
                                {modulesPath}
                                {customIsBusy}
                                {transportEnabled}
                                hasExistingI2P={hasExistingI2PInterface}
                                isEditing={isEditingInterface}
                                onpatch={(patch) => Object.assign(form, patch)}
                                onrefreshcomports={refreshComports}
                                onuploadmodule={handleUploadModule}
                                ondeletemodule={handleDeleteModule}
                            />
                        </div>

                        <!-- Interface Discovery Panel -->
                        <AddInterfaceDiscoveryPanel {discovery} onpatch={(patch) => Object.assign(discovery, patch)} />

                        <!-- Advanced Sections (Mode, IFAC, LoRa Calculations, Discovery Listener) -->
                        <AddInterfaceAdvancedPanel
                            interfaceType={newInterfaceType}
                            {sharedSettings}
                            {loraParams}
                            {reticulumDiscovery}
                            {savingDiscovery}
                            onpatchshared={(patch) => Object.assign(sharedSettings, patch)}
                            onpatchlora={(patch) => Object.assign(loraParams, patch)}
                            onpatchdiscovery={(patch) => Object.assign(reticulumDiscovery, patch)}
                            onsavediscovery={handleSaveDiscoveryPrefs}
                        />

                        <!-- Footer Save Action -->
                        <AddInterfaceFooter
                            isEditing={isEditingInterface}
                            {isSaving}
                            oncancel={navigateBack}
                            onsave={handleSave}
                        />
                    </div>
                </div>

                <!-- Right Sidebar (Community Nodes, Presets, Raw Config Import) -->
                <AddInterfaceSidebar
                    isEditing={isEditingInterface}
                    {communityInterfaces}
                    {communityFetchDone}
                    {showCommunityPresets}
                    onquickapply={applyConfig}
                    onhidecommunitypresets={() => (showCommunityPresets = false)}
                    onshowcommunitypresets={() => (showCommunityPresets = true)}
                />
            </div>
        </div>
    </div>
</div>
