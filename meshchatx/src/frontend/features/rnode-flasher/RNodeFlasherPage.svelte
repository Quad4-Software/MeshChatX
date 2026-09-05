<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import RNodeCapabilitiesBanner from "./components/RNodeCapabilitiesBanner.svelte";
    import RNodeSetupCard from "./components/RNodeSetupCard.svelte";
    import RNodeHelpFooter from "./components/RNodeHelpFooter.svelte";
    import RNodeAdvancedTools from "./components/RNodeAdvancedTools.svelte";
    import RNodeBluetoothPanel from "./components/RNodeBluetoothPanel.svelte";
    import RNodeTncPanel from "./components/RNodeTncPanel.svelte";
    import RNodeProvisionPanel from "./components/RNodeProvisionPanel.svelte";
    import RNodeDeviceDisplay from "./components/RNodeDeviceDisplay.svelte";
    import RNodeDiagnosticsPanel from "./components/RNodeDiagnosticsPanel.svelte";

    import RNode from "../../js/rnode/RNode.js";
    import ROM from "../../js/rnode/ROM.js";
    import Nrf52DfuFlasher from "../../js/rnode/Nrf52DfuFlasher.js";
    import RNodeUtils from "../../js/rnode/RNodeUtils.js";
    import products from "../../js/rnode/products.js";
    import {
        detectCapabilities,
        pickDefaultTransport,
        TRANSPORT_SERIAL,
        TRANSPORT_BLUETOOTH,
        TRANSPORT_WIFI,
    } from "../../js/rnode/Capabilities.js";
    import AndroidBridge from "../../js/rnode/AndroidBridge.js";
    import SerialTransport from "../../js/rnode/transports/SerialTransport.js";
    import BluetoothTransport from "../../js/rnode/transports/BluetoothTransport.js";
    import WifiTransport from "../../js/rnode/transports/WifiTransport.js";
    import { diagnose } from "../../js/rnode/Diagnostics.js";

    import ToastUtils from "../../js/ToastUtils.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import { t } from "../../js/i18n.js";
    import { displayBufferToPng } from "./lib/rnodeDisplay.js";
    import { loadVendorLibraries } from "./lib/rnodeVendorLibs.js";
    import { flashWifiOp, flashNrf52Op, flashEsp32Op } from "./lib/rnodeFlashOps.js";

    let capabilities = $state<any>(detectCapabilities());
    const androidBridge = new AndroidBridge();
    let connectionMethod = $state<string>(TRANSPORT_SERIAL);
    let wifiHost = $state("");
    let selectedProduct = $state<any | null>(null);
    let selectedModel = $state<any | null>(null);
    let firmwareFile = $state<File | null>(null);
    let isFlashing = $state(false);
    let flashingProgress = $state(0);
    let flashingStatus = $state("");
    let flashError = $state<string | null>(null);
    let isProvisioning = $state(false);
    let isSettingFirmwareHash = $state(false);
    let isEnteringDfuMode = $state(false);
    let rnodeDisplayImage = $state<string | null>(null);
    let showAdvanced = $state(false);
    let diagnostics = $state<any | null>(null);
    let connectedTransportLabel = $state<string | null>(null);
    let configFrequency = $state(917375000);
    let configBandwidth = $state(250000);
    let configTxPower = $state(22);
    let configSpreadingFactor = $state(11);
    const configCodingRate = 5;

    let onAndroidPermissionListener: ((event: any) => void) | null = null;

    let canFlash = $derived.by(() => {
        if (connectionMethod === TRANSPORT_WIFI) {
            return Boolean(wifiHost && firmwareFile);
        }
        if (connectionMethod === TRANSPORT_BLUETOOTH) {
            return false;
        }
        return Boolean(selectedProduct && selectedModel && firmwareFile);
    });

    let disabledAdvancedActions = $derived.by(() => {
        if (connectionMethod === TRANSPORT_WIFI) {
            return ["detect", "diagnose", "reboot", "read-display", "dump-eeprom", "wipe-eeprom"];
        }
        return [];
    });

    function refreshCapabilities(): void {
        capabilities = detectCapabilities();
    }

    async function onCapabilitiesAction(action: string): Promise<void> {
        if (action === "load-polyfill") {
            loadVendorLibraries(true).then(refreshCapabilities);
            ToastUtils.info(t("tools.rnode_flasher.support.actions.polyfill_loading"));
            return;
        }
        if (action === "open-native-flasher" || action === "request-usb") {
            if (androidBridge.openRNodeFlasher()) {
                ToastUtils.info(t("tools.rnode_flasher.support.actions.opened_native"));
            } else {
                ToastUtils.warning(t("tools.rnode_flasher.support.actions.open_native_failed"));
            }
            return;
        }
        if (action === "request-bluetooth") {
            const status = await androidBridge.requestPermission(AndroidBridge.PERM_BLUETOOTH);
            if (status === "granted") {
                ToastUtils.success(t("tools.rnode_flasher.support.actions.bluetooth_already_granted"));
            } else if (status === "settings") {
                ToastUtils.info(t("tools.rnode_flasher.support.actions.bluetooth_open_settings"));
            } else if (status === "requested") {
                ToastUtils.info(t("tools.rnode_flasher.support.actions.bluetooth_requested"));
            } else {
                ToastUtils.warning(t("tools.rnode_flasher.support.actions.bluetooth_unsupported"));
            }
            refreshCapabilities();
            return;
        }
        if (action === "open-bluetooth-settings") {
            if (androidBridge.openBluetoothSettings()) {
                ToastUtils.info(t("tools.rnode_flasher.support.actions.bluetooth_open_settings"));
            } else {
                ToastUtils.warning(t("tools.rnode_flasher.support.actions.bluetooth_settings_unavailable"));
            }
            return;
        }
        if (action === "recheck-capabilities") {
            refreshCapabilities();
            const bt = capabilities?.transports?.bluetooth;
            if (bt?.available) {
                ToastUtils.success(t("tools.rnode_flasher.support.actions.bluetooth_now_available"));
            } else {
                ToastUtils.info(t("tools.rnode_flasher.support.actions.bluetooth_still_unavailable"));
            }
            return;
        }
        if (action === "probe-bluetooth") {
            await probeWebBluetooth();
        }
    }

    async function probeWebBluetooth(): Promise<void> {
        refreshCapabilities();
        if (typeof window !== "undefined" && (window as any).isSecureContext === false) {
            ToastUtils.error(t("tools.rnode_flasher.support.bluetooth.insecure_context"));
            return;
        }
        if (!(navigator as any)?.bluetooth) {
            const reason = capabilities?.transports?.bluetooth?.reason;
            if (reason === "brave_flag_disabled") {
                ToastUtils.warning(t("tools.rnode_flasher.support.bluetooth.brave_enable_flag"));
            } else {
                ToastUtils.warning(t("tools.rnode_flasher.support.bluetooth.browser_unsupported"));
            }
            return;
        }
        try {
            await BluetoothTransport.request();
            connectionMethod = TRANSPORT_BLUETOOTH;
            refreshCapabilities();
            ToastUtils.success(t("tools.rnode_flasher.support.actions.bluetooth_probe_ok"));
        } catch (e: any) {
            if (e?.code === "NO_DEVICE_SELECTED") {
                ToastUtils.info(t("tools.rnode_flasher.support.actions.bluetooth_probe_cancelled"));
                return;
            }
            ToastUtils.error(
                t("tools.rnode_flasher.support.actions.bluetooth_probe_failed", {
                    error: e?.message || String(e),
                })
            );
        }
    }

    function requireWebSerialOrReopenNative(): void {
        if (typeof navigator !== "undefined" && (navigator as any).serial) {
            return;
        }
        if (androidBridge.hasNativeRNodeFlasher()) {
            androidBridge.openRNodeFlasher();
            const err: any = new Error(t("tools.rnode_flasher.errors.use_native_flasher"));
            err.code = "ANDROID_NATIVE_FLASHER_REQUIRED";
            throw err;
        }
    }

    async function openTransport(): Promise<any> {
        if (connectionMethod === TRANSPORT_SERIAL) {
            requireWebSerialOrReopenNative();
            const transport = await SerialTransport.request();
            await transport.open({ baudRate: 115200 });
            connectedTransportLabel = transport.description();
            return transport;
        }
        if (connectionMethod === TRANSPORT_BLUETOOTH) {
            if (androidBridge.isAvailable()) {
                const ok = androidBridge.hasPermission(AndroidBridge.PERM_BLUETOOTH);
                if (!ok) {
                    await androidBridge.requestPermission(AndroidBridge.PERM_BLUETOOTH);
                }
            }
            const transport = await BluetoothTransport.request();
            await transport.open();
            connectedTransportLabel = transport.description();
            return transport;
        }
        const transport = new WifiTransport(wifiHost);
        await transport.open();
        connectedTransportLabel = transport.description();
        return transport;
    }

    async function openRNode(): Promise<{ rnode: any; transport: any }> {
        const transport = await openTransport();
        const rnode = new RNode(transport);
        return { rnode, transport };
    }

    async function withRNode<T>(callback: (rnode: any) => Promise<T>): Promise<T | null> {
        let session: { rnode: any; transport: any } | null = null;
        try {
            session = await openRNode();
            const isRNode = await session.rnode.detect();
            if (!isRNode) {
                await session.rnode.close();
                flashError = t("tools.rnode_flasher.errors.not_an_rnode");
                ToastUtils.error(flashError);
                return null;
            }
            const result = await callback(session.rnode);
            await session.rnode.close();
            return result;
        } catch (e: any) {
            if (session?.rnode) {
                await session.rnode.close().catch(() => {});
            }
            throw e;
        } finally {
            connectedTransportLabel = null;
        }
    }

    async function detect(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                const ver = await rnode.getFirmwareVersion();
                ToastUtils.success(t("tools.rnode_flasher.alerts.rnode_detected", { version: ver }));
            });
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_detect_with_reason", { error: e.message || e }));
        }
    }

    async function runDiagnostics(): Promise<void> {
        try {
            const expectedProductId = selectedProduct?.id;
            const expectedModelId = selectedModel?.mapped_id ?? selectedModel?.id;
            const result = await withRNode(async (rnode) => {
                return diagnose(rnode, { expectedProductId, expectedModelId });
            });
            if (result) {
                diagnostics = result;
                if (result.issues.length === 0) {
                    ToastUtils.success(t("tools.rnode_flasher.alerts.diagnostics_healthy"));
                } else {
                    ToastUtils.warning(
                        t("tools.rnode_flasher.alerts.diagnostics_issues", { count: result.issues.length })
                    );
                }
            }
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_diagnostics", { error: e.message || e }));
        }
    }

    async function reboot(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                await rnode.reset();
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.rebooting"));
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_reboot", { error: e.message || e }));
        }
    }

    async function readDisplay(): Promise<void> {
        try {
            const buffer = await withRNode(async (rnode) => {
                return rnode.readDisplay();
            });
            if (buffer) {
                rnodeDisplayImage = displayBufferToPng(buffer);
            }
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_read_display", { error: e.message || e }));
        }
    }

    async function dumpEeprom(): Promise<void> {
        try {
            const eeprom = await withRNode(async (rnode) => rnode.getRom());
            if (eeprom) {
                console.log(RNodeUtils.bytesToHex(eeprom));
                ToastUtils.success(t("tools.rnode_flasher.alerts.eeprom_dumped"));
            }
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_dump_eeprom", { error: e.message || e }));
        }
    }

    async function wipeEeprom(): Promise<void> {
        if (!(await DialogUtils.confirm(t("tools.rnode_flasher.alerts.eeprom_wipe_confirm")))) {
            return;
        }
        try {
            await withRNode(async (rnode) => {
                await rnode.wipeRom();
                await rnode.reset();
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.eeprom_wiped"));
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_wipe_eeprom", { error: e.message || e }));
        }
    }

    function onAdvancedAction(action: string): void {
        const map: Record<string, () => Promise<void>> = {
            detect,
            diagnose: runDiagnostics,
            reboot,
            "read-display": readDisplay,
            "dump-eeprom": dumpEeprom,
            "wipe-eeprom": wipeEeprom,
        };
        map[action]?.();
    }

    function onBluetoothAction(action: string): void {
        const map: Record<string, () => Promise<void>> = {
            "enable-bluetooth": enableBluetooth,
            "disable-bluetooth": disableBluetooth,
            "pair-bluetooth": startBluetoothPairing,
        };
        map[action]?.();
    }

    function onTncAction(action: string): void {
        if (action === "enable-tnc") enableTncMode();
        if (action === "disable-tnc") disableTncMode();
    }

    async function enterDfuMode(): Promise<void> {
        isEnteringDfuMode = true;
        flashError = null;
        try {
            requireWebSerialOrReopenNative();
            const transport = await SerialTransport.request();
            const flasher = new Nrf52DfuFlasher(transport.port);
            await flasher.enterDfuMode();
            ToastUtils.success(t("tools.rnode_flasher.alerts.dfu_ready"));
        } catch (e: any) {
            flashError = t("tools.rnode_flasher.errors.failed_dfu", { error: e.message || e });
            ToastUtils.error(flashError);
        } finally {
            isEnteringDfuMode = false;
        }
    }

    async function flash(): Promise<void> {
        flashError = null;
        if (!firmwareFile) {
            flashError = t("tools.rnode_flasher.errors.select_firmware_first");
            ToastUtils.error(flashError);
            return;
        }
        if (connectionMethod === TRANSPORT_WIFI) {
            await flashWifi();
            return;
        }
        if (connectionMethod === TRANSPORT_BLUETOOTH) {
            flashError = t("tools.rnode_flasher.errors.bluetooth_flash_unsupported");
            ToastUtils.error(flashError);
            return;
        }
        switch (selectedProduct?.platform) {
            case ROM.PLATFORM_ESP32:
                await flashEsp32();
                break;
            case ROM.PLATFORM_NRF52:
                await flashNrf52();
                break;
            default:
                ToastUtils.error(t("tools.rnode_flasher.errors.select_product_first"));
        }
    }

    async function flashWifi(): Promise<void> {
        if (!firmwareFile) return;
        isFlashing = true;
        flashingProgress = 0;
        flashingStatus = t("tools.rnode_flasher.preparing_firmware");
        try {
            await flashWifiOp(wifiHost, firmwareFile, selectedProduct, selectedModel, (pct, status) => {
                flashingProgress = pct;
                flashingStatus = status;
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.flash_success"));
        } catch (e: any) {
            flashError = t("tools.rnode_flasher.errors.failed_ota", { error: e.message || e });
            ToastUtils.error(flashError);
        } finally {
            isFlashing = false;
            flashingStatus = "";
        }
    }

    async function flashNrf52(): Promise<void> {
        if (!firmwareFile) return;
        isFlashing = true;
        flashingProgress = 0;
        flashingStatus = t("tools.rnode_flasher.connecting_device");
        try {
            requireWebSerialOrReopenNative();
            await flashNrf52Op(firmwareFile, (pct, status) => {
                flashingProgress = pct;
                flashingStatus = status;
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.flash_success"));
        } catch (e: any) {
            flashError = t("tools.rnode_flasher.errors.failed_flash", { error: e.message || e });
            ToastUtils.error(flashError);
        } finally {
            isFlashing = false;
            flashingStatus = "";
        }
    }

    async function flashEsp32(): Promise<void> {
        if (!firmwareFile) return;
        isFlashing = true;
        flashingProgress = 0;
        flashingStatus = t("tools.rnode_flasher.connecting_device");
        try {
            requireWebSerialOrReopenNative();
            await flashEsp32Op(firmwareFile, selectedProduct, selectedModel, (pct, status) => {
                flashingProgress = pct;
                flashingStatus = status;
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.flash_success"));
        } catch (e: any) {
            flashError = t("tools.rnode_flasher.errors.failed_flash", { error: e.message || e });
            ToastUtils.error(flashError);
        } finally {
            isFlashing = false;
            flashingStatus = "";
        }
    }

    async function provision(): Promise<void> {
        try {
            isProvisioning = true;
            await withRNode(async (rnode) => {
                const rom = await rnode.getRomAsObject();
                if (rom.parse()) {
                    ToastUtils.error(t("tools.rnode_flasher.errors.provisioned_already"));
                    return;
                }
                if (!selectedProduct || !selectedModel) {
                    ToastUtils.error(t("tools.rnode_flasher.errors.select_product_first"));
                    return;
                }
                const product = selectedProduct.id;
                const model = selectedModel.mapped_id ?? selectedModel.id;
                const hwRev = 0x1;
                const serial = 1;
                const now = Math.floor(Date.now() / 1000);
                const sBytes = RNodeUtils.packUInt32BE(serial);
                const tBytes = RNodeUtils.packUInt32BE(now);
                const checksum = RNodeUtils.md5([product, model, hwRev, ...sBytes, ...tBytes]);

                await rnode.writeRom(ROM.ADDR_PRODUCT, product);
                await rnode.writeRom(ROM.ADDR_MODEL, model);
                await rnode.writeRom(ROM.ADDR_HW_REV, hwRev);
                for (let i = 0; i < 4; i++) {
                    await rnode.writeRom(ROM.ADDR_SERIAL + i, sBytes[i]);
                    await rnode.writeRom(ROM.ADDR_MADE + i, tBytes[i]);
                }
                for (let i = 0; i < 16; i++) await rnode.writeRom(ROM.ADDR_CHKSUM + i, checksum[i]);
                for (let i = 0; i < 128; i++) await rnode.writeRom(ROM.ADDR_SIGNATURE + i, 0x00);
                await rnode.writeRom(ROM.ADDR_INFO_LOCK, ROM.INFO_LOCK_BYTE);

                await RNodeUtils.sleepMillis(5000);
                await rnode.reset();
                ToastUtils.success(t("tools.rnode_flasher.alerts.provision_success"));
            });
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_provision", { error: e.message || e }));
        } finally {
            isProvisioning = false;
        }
    }

    async function setFirmwareHash(): Promise<void> {
        try {
            isSettingFirmwareHash = true;
            await withRNode(async (rnode) => {
                const rom = await rnode.getRomAsObject();
                if (!rom.parse()) {
                    ToastUtils.error(t("tools.rnode_flasher.errors.not_provisioned"));
                    return;
                }
                const hash = await rnode.getFirmwareHash();
                await rnode.setFirmwareHash(hash);
                await RNodeUtils.sleepMillis(5000);
                await rnode.reset().catch(() => {});
                ToastUtils.success(t("tools.rnode_flasher.alerts.hash_success"));
            });
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_set_hash", { error: e.message || e }));
        } finally {
            isSettingFirmwareHash = false;
        }
    }

    async function enableTncMode(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                await rnode.setFrequency(configFrequency);
                await rnode.setBandwidth(configBandwidth);
                await rnode.setTxPower(configTxPower);
                await rnode.setSpreadingFactor(configSpreadingFactor);
                await rnode.setCodingRate(configCodingRate);
                await rnode.setRadioStateOn();
                await RNodeUtils.sleepMillis(500);
                await rnode.saveConfig();
                await rnode.saveConfig();
                await RNodeUtils.sleepMillis(5000);
                await rnode.reset();
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.tnc_enabled"));
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_enable_tnc", { error: e.message || e }));
        }
    }

    async function disableTncMode(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                await rnode.deleteConfig();
                await RNodeUtils.sleepMillis(5000);
                await rnode.reset();
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.tnc_disabled"));
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_disable_tnc", { error: e.message || e }));
        }
    }

    async function enableBluetooth(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                await rnode.enableBluetooth();
                await RNodeUtils.sleepMillis(1000);
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.bluetooth_enabled"));
        } catch (e: any) {
            ToastUtils.error(
                t("tools.rnode_flasher.errors.failed_enable_bluetooth", {
                    error: e.message || e,
                })
            );
        }
    }

    async function disableBluetooth(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                await rnode.disableBluetooth();
                await RNodeUtils.sleepMillis(1000);
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.bluetooth_disabled"));
        } catch (e: any) {
            ToastUtils.error(
                t("tools.rnode_flasher.errors.failed_disable_bluetooth", {
                    error: e.message || e,
                })
            );
        }
    }

    async function startBluetoothPairing(): Promise<void> {
        try {
            await withRNode(async (rnode) => {
                await rnode.startBluetoothPairing((pin: string) => {
                    ToastUtils.success(t("tools.rnode_flasher.alerts.bluetooth_pairing_pin", { pin }));
                });
            });
            ToastUtils.success(t("tools.rnode_flasher.alerts.bluetooth_pairing_started"));
        } catch (e: any) {
            ToastUtils.error(t("tools.rnode_flasher.errors.failed_start_pairing", { error: e.message || e }));
        }
    }

    onMount(() => {
        onAndroidPermissionListener = (event: any) => {
            const detail = event?.detail;
            if (!detail) {
                return;
            }
            refreshCapabilities();
            if (detail.group === "bluetooth") {
                if (detail.granted) {
                    ToastUtils.success(t("tools.rnode_flasher.support.actions.bluetooth_granted"));
                } else {
                    ToastUtils.warning(t("tools.rnode_flasher.support.actions.bluetooth_denied"));
                }
            }
        };
        window.addEventListener("meshchatx-android-permission", onAndroidPermissionListener);
        if (androidBridge.hasNativeRNodeFlasher()) {
            androidBridge.openRNodeFlasher();
            ToastUtils.info(t("tools.rnode_flasher.support.actions.opened_native"));
        }
        refreshCapabilities();
        connectionMethod = pickDefaultTransport(capabilities);
        void loadVendorLibraries().then(refreshCapabilities);
    });

    onDestroy(() => {
        if (onAndroidPermissionListener) {
            window.removeEventListener("meshchatx-android-permission", onAndroidPermissionListener);
        }
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="lightning-bolt"
        title={t("tools.rnode_flasher.title")}
        description={t("tools.rnode_flasher.description")}
        accent="purple"
    >
        {#if connectedTransportLabel}
            <span
                class="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
            >
                <MaterialDesignIcon iconName="link-variant" class="size-3" />
                {connectedTransportLabel}
            </span>
        {/if}
        <button
            type="button"
            data-testid="rnode-advanced-toggle"
            class="p-2 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors flex items-center gap-2 text-sm font-medium cursor-pointer"
            onclick={() => (showAdvanced = !showAdvanced)}
        >
            <MaterialDesignIcon iconName={showAdvanced ? "cog" : "cog-outline"} class="size-5" />
            <span class="hidden sm:inline">
                {showAdvanced ? t("tools.rnode_flasher.simple") : t("tools.rnode_flasher.advanced")}
            </span>
        </button>
        <a
            href="/rnode-flasher/index.html"
            target="_blank"
            class="p-2 text-gray-500 hover:bg-sem-surface-muted rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
            title={t("tools.rnode_flasher.open_original_tab")}
        >
            <MaterialDesignIcon iconName="open-in-new" class="size-5" />
            <span class="hidden sm:inline">{t("tools.rnode_flasher.original")}</span>
        </a>
    </ToolsPageHeader>

    <div
        class="flex-1 min-h-0 min-w-0 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
    >
        <RNodeCapabilitiesBanner
            {capabilities}
            androidAvailable={androidBridge.isAvailable()}
            onaction={onCapabilitiesAction}
        />

        <RNodeDiagnosticsPanel {diagnostics} />

        <!-- setup card -->
        <RNodeSetupCard
            bind:connectionMethod
            bind:wifiHost
            bind:selectedProduct
            bind:selectedModel
            bind:firmwareFile
            {products}
            {capabilities}
            {isEnteringDfuMode}
            {canFlash}
            {isFlashing}
            {flashingProgress}
            {flashingStatus}
            {flashError}
            onenterDfu={() => void enterDfuMode()}
            onflash={() => void flash()}
        />

        <!-- provision/finalize -->
        {#if showAdvanced || isProvisioning || isSettingFirmwareHash}
            <div class="border border-sem-border bg-sem-surface rounded-lg p-4 sm:p-6 space-y-6">
                <RNodeProvisionPanel
                    provisionStepNumber={3}
                    canProvision={Boolean(selectedProduct && selectedModel)}
                    {isProvisioning}
                    {isSettingFirmwareHash}
                    onprovision={() => void provision()}
                    onsetHash={() => void setFirmwareHash()}
                />

                {#if showAdvanced}
                    <div class="pt-6 border-t border-sem-border space-y-4">
                        <RNodeAdvancedTools disabledActions={disabledAdvancedActions} onaction={onAdvancedAction} />
                        <RNodeDeviceDisplay image={rnodeDisplayImage} onclear={() => (rnodeDisplayImage = null)} />
                    </div>
                {/if}
            </div>
        {/if}

        <!-- config cards -->
        {#if showAdvanced}
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <RNodeBluetoothPanel onaction={onBluetoothAction} />
                <RNodeTncPanel
                    bind:frequency={configFrequency}
                    bind:bandwidth={configBandwidth}
                    bind:txPower={configTxPower}
                    bind:spreadingFactor={configSpreadingFactor}
                    onaction={onTncAction}
                />
            </div>
        {/if}

        <RNodeHelpFooter />
    </div>
</div>
