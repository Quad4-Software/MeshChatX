<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col h-full w-full bg-slate-50 dark:bg-zinc-950 overflow-hidden min-w-0">
        <!-- header -->
        <div
            class="flex flex-wrap items-center gap-2 px-3 sm:px-4 md:px-6 py-2 sm:py-3 border-b border-gray-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-950 z-10 relative"
        >
            <div class="flex items-center gap-2 min-w-0 flex-1">
                <v-icon icon="mdi-chip" color="purple" size="24" class="shrink-0"></v-icon>
                <h1 class="text-lg sm:text-xl font-black text-gray-900 dark:text-white truncate">
                    {{ $t("tools.rnode_flasher.title") }}
                </h1>
                <span
                    v-if="connectedTransportLabel"
                    class="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
                >
                    <MaterialDesignIcon icon-name="link-variant" class="size-3" />
                    {{ connectedTransportLabel }}
                </span>
            </div>

            <div class="ml-auto flex flex-wrap items-center justify-end gap-1 sm:gap-2 shrink-0">
                <button
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
                    @click="showAdvanced = !showAdvanced"
                >
                    <MaterialDesignIcon :icon-name="showAdvanced ? 'cog' : 'cog-outline'" class="size-5" />
                    <span class="hidden sm:inline">
                        {{ showAdvanced ? $t("tools.rnode_flasher.simple") : $t("tools.rnode_flasher.advanced") }}
                    </span>
                </button>
                <a
                    href="/rnode-flasher/index.html"
                    target="_blank"
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
                    :title="$t('tools.rnode_flasher.open_original_tab')"
                >
                    <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                    <span class="hidden sm:inline">{{ $t("tools.rnode_flasher.original") }}</span>
                </a>
                <button
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                    @click="$router.push({ name: 'tools' })"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>
        </div>

        <!-- content -->
        <div
            class="flex-1 min-h-0 min-w-0 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <RNodeCapabilitiesBanner
                :capabilities="capabilities"
                :android-available="androidBridge.isAvailable()"
                @action="onCapabilitiesAction"
            />

            <RNodeDiagnosticsPanel :diagnostics="diagnostics" />

            <!-- setup card -->
            <div
                class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-lg overflow-hidden"
            >
                <div class="grid grid-cols-1 md:grid-cols-2">
                    <div class="p-4 sm:p-6 border-b md:border-b-0 md:border-r border-gray-100 dark:border-zinc-800">
                        <RNodeDeviceSelector
                            :step-number="1"
                            :connection-method="connectionMethod"
                            :wifi-host="wifiHost"
                            :selected-product="selectedProduct"
                            :selected-model="selectedModel"
                            :products="products"
                            :capabilities="capabilities"
                            :is-entering-dfu-mode="isEnteringDfuMode"
                            @update:connection-method="connectionMethod = $event"
                            @update:wifi-host="wifiHost = $event"
                            @update:selected-product="onSelectedProductChange"
                            @update:selected-model="selectedModel = $event"
                            @enter-dfu="enterDfuMode"
                        />
                    </div>
                    <div class="p-4 sm:p-6 bg-gray-50/50 dark:bg-zinc-900/50">
                        <RNodeFirmwareSelector
                            ref="firmwareSelector"
                            :step-number="2"
                            :recommended-firmware-filename="recommendedFirmwareFilename"
                            :latest-release="latestRelease"
                            :is-downloading-firmware="isDownloadingFirmware"
                            :firmware-file="firmwareFile"
                            @update:firmware-file="firmwareFile = $event"
                            @download-recommended="downloadRecommendedFirmware"
                        />
                        <div class="mt-4">
                            <RNodeFlashAction
                                :can-flash="canFlash"
                                :is-flashing="isFlashing"
                                :flashing-progress="flashingProgress"
                                :flashing-status="flashingStatus"
                                :error-message="flashError"
                                @flash="flash"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <!-- provision/finalize -->
            <div
                v-if="showAdvanced || isProvisioning || isSettingFirmwareHash"
                class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-lg p-4 sm:p-6 space-y-6"
            >
                <RNodeProvisionPanel
                    :provision-step-number="3"
                    :can-provision="!!selectedProduct && !!selectedModel"
                    :is-provisioning="isProvisioning"
                    :is-setting-firmware-hash="isSettingFirmwareHash"
                    @provision="provision"
                    @set-hash="setFirmwareHash"
                />

                <div v-if="showAdvanced" class="pt-6 border-t border-gray-100 dark:border-zinc-800 space-y-4">
                    <RNodeAdvancedTools :disabled-actions="disabledAdvancedActions" @action="onAdvancedAction" />
                    <RNodeDeviceDisplay :image="rnodeDisplayImage" @clear="rnodeDisplayImage = null" />
                </div>
            </div>

            <!-- config cards -->
            <div v-if="showAdvanced" class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <RNodeBluetoothPanel @action="onBluetoothAction" />
                <RNodeTncPanel
                    v-model:frequency="configFrequency"
                    v-model:bandwidth="configBandwidth"
                    v-model:tx-power="configTxPower"
                    v-model:spreading-factor="configSpreadingFactor"
                    @action="onTncAction"
                />
            </div>

            <!-- help footer -->
            <div
                class="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-zinc-50 dark:bg-zinc-900/30"
            >
                <div class="flex items-center gap-3 text-sm text-zinc-500">
                    <MaterialDesignIcon icon-name="help-circle-outline" class="size-5" />
                    <span>{{ $t("tools.rnode_flasher.find_device_issue") }}</span>
                </div>
                <div class="flex items-center gap-4">
                    <a
                        target="_blank"
                        :href="`${giteaBaseUrl}/Reticulum/rnode-flasher`"
                        class="text-blue-500 hover:underline text-sm font-bold"
                        >RNode Flasher GH</a
                    >
                    <a
                        target="_blank"
                        :href="`${giteaBaseUrl}/Reticulum/RNode_Firmware`"
                        class="text-blue-500 hover:underline text-sm font-bold"
                        >RNode Firmware GH</a
                    >
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import RNodeCapabilitiesBanner from "../rnode/RNodeCapabilitiesBanner.vue";
import RNodeDeviceSelector from "../rnode/RNodeDeviceSelector.vue";
import RNodeFirmwareSelector from "../rnode/RNodeFirmwareSelector.vue";
import RNodeFlashAction from "../rnode/RNodeFlashAction.vue";
import RNodeAdvancedTools from "../rnode/RNodeAdvancedTools.vue";
import RNodeBluetoothPanel from "../rnode/RNodeBluetoothPanel.vue";
import RNodeTncPanel from "../rnode/RNodeTncPanel.vue";
import RNodeProvisionPanel from "../rnode/RNodeProvisionPanel.vue";
import RNodeDeviceDisplay from "../rnode/RNodeDeviceDisplay.vue";
import RNodeDiagnosticsPanel from "../rnode/RNodeDiagnosticsPanel.vue";

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
import GlobalState from "../../js/GlobalState";

export default {
    name: "RNodeFlasherPage",
    components: {
        MaterialDesignIcon,
        RNodeCapabilitiesBanner,
        RNodeDeviceSelector,
        RNodeFirmwareSelector,
        RNodeFlashAction,
        RNodeAdvancedTools,
        RNodeBluetoothPanel,
        RNodeTncPanel,
        RNodeProvisionPanel,
        RNodeDeviceDisplay,
        RNodeDiagnosticsPanel,
    },
    data() {
        return {
            capabilities: detectCapabilities(),
            androidBridge: new AndroidBridge(),
            connectionMethod: TRANSPORT_SERIAL,
            wifiHost: "",
            selectedProduct: null,
            selectedModel: null,
            products,
            firmwareFile: null,
            isFlashing: false,
            flashingProgress: 0,
            flashingStatus: "",
            flashError: null,
            isProvisioning: false,
            isSettingFirmwareHash: false,
            isEnteringDfuMode: false,
            isDownloadingFirmware: false,
            rnodeDisplayImage: null,
            showAdvanced: false,
            latestRelease: null,
            diagnostics: null,
            connectedTransportLabel: null,
            configFrequency: 917375000,
            configBandwidth: 250000,
            configTxPower: 22,
            configSpreadingFactor: 11,
            configCodingRate: 5,
        };
    },
    computed: {
        recommendedFirmwareFilename() {
            return this.selectedModel?.firmware_filename ?? this.selectedProduct?.firmware_filename;
        },
        giteaBaseUrl() {
            return GlobalState.config?.gitea_base_url || "https://git.quad4.io";
        },
        canFlash() {
            if (this.connectionMethod === TRANSPORT_WIFI) {
                return Boolean(this.wifiHost && this.firmwareFile);
            }
            if (this.connectionMethod === TRANSPORT_BLUETOOTH) {
                return false;
            }
            return Boolean(this.selectedProduct && this.selectedModel && this.firmwareFile);
        },
        disabledAdvancedActions() {
            if (this.connectionMethod === TRANSPORT_WIFI) {
                return ["detect", "diagnose", "reboot", "read-display", "dump-eeprom", "wipe-eeprom"];
            }
            return [];
        },
    },
    mounted() {
        this.refreshCapabilities();
        this.connectionMethod = pickDefaultTransport(this.capabilities);
        this.loadVendorLibraries();
        this.fetchLatestRelease();
    },
    methods: {
        refreshCapabilities() {
            this.capabilities = detectCapabilities();
        },
        onSelectedProductChange(product) {
            this.selectedProduct = product;
            this.selectedModel = null;
        },
        onCapabilitiesAction(action) {
            if (action === "load-polyfill") {
                this.loadVendorLibraries(true);
                ToastUtils.info(this.$t("tools.rnode_flasher.support.actions.polyfill_loading"));
                return;
            }
            if (action === "request-bluetooth") {
                this.androidBridge.requestPermission(AndroidBridge.PERM_BLUETOOTH);
                ToastUtils.info(this.$t("tools.rnode_flasher.support.actions.bluetooth_requested"));
                return;
            }
            if (action === "open-bluetooth-settings") {
                this.androidBridge.openBluetoothSettings();
            }
        },
        async fetchLatestRelease() {
            try {
                const response = await fetch(
                    "/api/v1/tools/rnode/latest_release?repo=Reticulum/RNode_Firmware"
                );
                if (response.ok) {
                    this.latestRelease = await response.json();
                }
            } catch {
                // offline-friendly: silently ignore so the rest of the page still works
            }
        },
        _resolveRecommendedAssetUrl() {
            const filename = this.recommendedFirmwareFilename;
            if (!filename) return null;
            const asset = this.latestRelease?.assets?.find((a) => a.name === filename);
            if (asset?.browser_download_url) {
                return asset.browser_download_url;
            }
            const base = (this.giteaBaseUrl || "https://git.quad4.io").replace(/\/$/, "");
            return `${base}/Reticulum/RNode_Firmware/releases/latest/download/${filename}`;
        },
        async downloadRecommendedFirmware() {
            const assetUrl = this._resolveRecommendedAssetUrl();
            if (!assetUrl) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.firmware_not_found_in_release"));
                return;
            }
            this.isDownloadingFirmware = true;
            try {
                const downloadUrl = `/api/v1/tools/rnode/download_firmware?url=${encodeURIComponent(assetUrl)}`;
                const response = await fetch(downloadUrl);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: response.statusText }));
                    throw new Error(errorData.error || `Download failed with status ${response.status}`);
                }
                const blob = await response.blob();
                const file = new File([blob], this.recommendedFirmwareFilename, { type: "application/zip" });
                this.firmwareFile = file;
                this.$refs.firmwareSelector?.setFile(file);
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.firmware_downloaded"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_download", { error: e.message || e }));
            } finally {
                this.isDownloadingFirmware = false;
            }
        },
        async loadVendorLibraries(force = false) {
            if (!force && window.zip && window.CryptoJS && window.ESPLoader) return;
            const libs = [
                "/rnode-flasher/js/zip.min.js",
                "/rnode-flasher/js/crypto-js@3.9.1-1/core.js",
                "/rnode-flasher/js/crypto-js@3.9.1-1/md5.js",
            ];
            for (const lib of libs) {
                try {
                    await this._loadScript(lib);
                } catch {
                    // continue best-effort; loadVendorLibraries is best-effort and
                    // missing assets surface later through clear error toasts
                }
            }
            try {
                const esptoolPath = "/rnode-flasher/js/esptool-js@0.4.5/bundle.js";
                const esptool = await import(/* @vite-ignore */ esptoolPath);
                window.ESPLoader = esptool.ESPLoader;
                window.Transport = esptool.Transport;

                const serialPolyfillPath = "/rnode-flasher/js/web-serial-polyfill@1.0.15/dist/serial.js";
                const serialPolyfill = await import(/* @vite-ignore */ serialPolyfillPath);
                if (serialPolyfill.serial) {
                    window.serial = serialPolyfill.serial;
                }
            } catch (e) {
                console.error("Failed to load ES module vendor libraries:", e);
            }
            if (!navigator.serial && navigator.usb && window.serial) {
                navigator.serial = window.serial;
            }
            this.refreshCapabilities();
        },
        _loadScript(src) {
            return new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.src = src;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        },
        async _openTransport() {
            if (this.connectionMethod === TRANSPORT_SERIAL) {
                const transport = await SerialTransport.request();
                await transport.open({ baudRate: 115200 });
                this.connectedTransportLabel = transport.description();
                return transport;
            }
            if (this.connectionMethod === TRANSPORT_BLUETOOTH) {
                if (this.androidBridge.isAvailable()) {
                    const ok = this.androidBridge.hasPermission(AndroidBridge.PERM_BLUETOOTH);
                    if (!ok) {
                        await this.androidBridge.requestPermission(AndroidBridge.PERM_BLUETOOTH);
                    }
                }
                const transport = await BluetoothTransport.request();
                await transport.open();
                this.connectedTransportLabel = transport.description();
                return transport;
            }
            const transport = new WifiTransport(this.wifiHost);
            await transport.open();
            this.connectedTransportLabel = transport.description();
            return transport;
        },
        async _openRNode() {
            const transport = await this._openTransport();
            const rnode = new RNode(transport);
            return { rnode, transport };
        },
        async _withRNode(callback) {
            let session = null;
            try {
                session = await this._openRNode();
                const isRNode = await session.rnode.detect();
                if (!isRNode) {
                    await session.rnode.close();
                    this.flashError = this.$t("tools.rnode_flasher.errors.not_an_rnode");
                    ToastUtils.error(this.flashError);
                    return null;
                }
                const result = await callback(session.rnode);
                await session.rnode.close();
                return result;
            } catch (e) {
                if (session?.rnode) {
                    await session.rnode.close().catch(() => {});
                }
                throw e;
            } finally {
                this.connectedTransportLabel = null;
            }
        },
        async detect() {
            try {
                await this._withRNode(async (rnode) => {
                    const ver = await rnode.getFirmwareVersion();
                    ToastUtils.success(this.$t("tools.rnode_flasher.alerts.rnode_detected", { version: ver }));
                });
            } catch (e) {
                ToastUtils.error(
                    this.$t("tools.rnode_flasher.errors.failed_detect_with_reason", { error: e.message || e })
                );
            }
        },
        async runDiagnostics() {
            try {
                const expectedProductId = this.selectedProduct?.id;
                const expectedModelId = this.selectedModel?.mapped_id ?? this.selectedModel?.id;
                const result = await this._withRNode(async (rnode) => {
                    return diagnose(rnode, { expectedProductId, expectedModelId });
                });
                if (result) {
                    this.diagnostics = result;
                    if (result.issues.length === 0) {
                        ToastUtils.success(this.$t("tools.rnode_flasher.alerts.diagnostics_healthy"));
                    } else {
                        ToastUtils.warning(
                            this.$t("tools.rnode_flasher.alerts.diagnostics_issues", { count: result.issues.length })
                        );
                    }
                }
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_diagnostics", { error: e.message || e }));
            }
        },
        async reboot() {
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.reset();
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.rebooting"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_reboot", { error: e.message || e }));
            }
        },
        async readDisplay() {
            try {
                const buffer = await this._withRNode(async (rnode) => {
                    return rnode.readDisplay();
                });
                if (buffer) {
                    this.rnodeDisplayImage = this._displayBufferToPng(buffer);
                }
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_read_display", { error: e.message || e }));
            }
        },
        async dumpEeprom() {
            try {
                const eeprom = await this._withRNode(async (rnode) => rnode.getRom());
                if (eeprom) {
                    console.log(RNodeUtils.bytesToHex(eeprom));
                    ToastUtils.success(this.$t("tools.rnode_flasher.alerts.eeprom_dumped"));
                }
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_dump_eeprom", { error: e.message || e }));
            }
        },
        async wipeEeprom() {
            if (!confirm(this.$t("tools.rnode_flasher.alerts.eeprom_wipe_confirm"))) {
                return;
            }
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.wipeRom();
                    await rnode.reset();
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.eeprom_wiped"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_wipe_eeprom", { error: e.message || e }));
            }
        },
        onAdvancedAction(action) {
            const map = {
                detect: this.detect,
                diagnose: this.runDiagnostics,
                reboot: this.reboot,
                "read-display": this.readDisplay,
                "dump-eeprom": this.dumpEeprom,
                "wipe-eeprom": this.wipeEeprom,
            };
            map[action]?.();
        },
        onBluetoothAction(action) {
            const map = {
                "enable-bluetooth": this.enableBluetooth,
                "disable-bluetooth": this.disableBluetooth,
                "pair-bluetooth": this.startBluetoothPairing,
            };
            map[action]?.();
        },
        onTncAction(action) {
            if (action === "enable-tnc") this.enableTncMode();
            if (action === "disable-tnc") this.disableTncMode();
        },
        async enterDfuMode() {
            this.isEnteringDfuMode = true;
            this.flashError = null;
            try {
                const transport = await SerialTransport.request();
                const flasher = new Nrf52DfuFlasher(transport.port);
                await flasher.enterDfuMode();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.dfu_ready"));
            } catch (e) {
                this.flashError = this.$t("tools.rnode_flasher.errors.failed_dfu", { error: e.message || e });
                ToastUtils.error(this.flashError);
            } finally {
                this.isEnteringDfuMode = false;
            }
        },
        async flash() {
            this.flashError = null;
            if (!this.firmwareFile) {
                this.flashError = this.$t("tools.rnode_flasher.errors.select_firmware_first");
                ToastUtils.error(this.flashError);
                return;
            }
            if (this.connectionMethod === TRANSPORT_WIFI) {
                await this._flashWifi();
                return;
            }
            if (this.connectionMethod === TRANSPORT_BLUETOOTH) {
                this.flashError = this.$t("tools.rnode_flasher.errors.bluetooth_flash_unsupported");
                ToastUtils.error(this.flashError);
                return;
            }
            switch (this.selectedProduct?.platform) {
                case ROM.PLATFORM_ESP32:
                    await this._flashEsp32();
                    break;
                case ROM.PLATFORM_NRF52:
                    await this._flashNrf52();
                    break;
                default:
                    ToastUtils.error(this.$t("tools.rnode_flasher.errors.select_product_first"));
            }
        },
        async _flashWifi() {
            if (!WifiTransport.isValidHost(this.wifiHost)) {
                this.flashError = this.$t("tools.rnode_flasher.errors.invalid_host");
                ToastUtils.error(this.flashError);
                return;
            }
            this.isFlashing = true;
            this.flashingProgress = 0;
            this.flashingStatus = this.$t("tools.rnode_flasher.preparing_firmware");
            try {
                const flashConfig = this.selectedModel?.flash_config ?? this.selectedProduct?.flash_config;
                const blobReader = new window.zip.BlobReader(this.firmwareFile);
                const zipReader = new window.zip.ZipReader(blobReader);
                const zipEntries = await zipReader.getEntries();

                let mainBinFilename = flashConfig?.flash_files?.["0x10000"];
                if (!mainBinFilename) {
                    const binEntry = zipEntries.find(
                        (e) =>
                            e.filename.endsWith(".bin") &&
                            !e.filename.includes("bootloader") &&
                            !e.filename.includes("partitions")
                    );
                    if (binEntry) mainBinFilename = binEntry.filename;
                }
                if (!mainBinFilename) {
                    throw new Error(this.$t("tools.rnode_flasher.errors.no_main_bin"));
                }
                const entry = zipEntries.find((e) => e.filename === mainBinFilename);
                if (!entry) {
                    throw new Error(this.$t("tools.rnode_flasher.errors.failed_extract", { file: mainBinFilename }));
                }
                const binBlob = await entry.getData(new window.zip.BlobWriter());

                const transport = new WifiTransport(this.wifiHost);
                await transport.upload(binBlob, (percentage) => {
                    this.flashingProgress = percentage;
                    this.flashingStatus = this.$t("tools.rnode_flasher.uploading", { percentage });
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.flash_success"));
            } catch (e) {
                this.flashError = this.$t("tools.rnode_flasher.errors.failed_ota", { error: e.message || e });
                ToastUtils.error(this.flashError);
            } finally {
                this.isFlashing = false;
                this.flashingStatus = "";
            }
        },
        async _flashNrf52() {
            this.isFlashing = true;
            this.flashingProgress = 0;
            this.flashingStatus = this.$t("tools.rnode_flasher.connecting_device");
            let transport = null;
            try {
                transport = await SerialTransport.request();
                const flasher = new Nrf52DfuFlasher(transport.port);
                await flasher.flash(this.firmwareFile, (percentage, message) => {
                    this.flashingProgress = percentage;
                    this.flashingStatus = message || this.$t("tools.rnode_flasher.flashing", { percentage });
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.flash_success"));
            } catch (e) {
                this.flashError = this.$t("tools.rnode_flasher.errors.failed_flash", { error: e.message || e });
                ToastUtils.error(this.flashError);
            } finally {
                this.isFlashing = false;
                this.flashingStatus = "";
                if (transport) await transport.close().catch(() => {});
            }
        },
        async _flashEsp32() {
            if (!window.ESPLoader) {
                this.flashError = this.$t("tools.rnode_flasher.errors.esptool_not_loaded");
                ToastUtils.error(this.flashError);
                return;
            }
            const flashConfig = this.selectedModel?.flash_config ?? this.selectedProduct?.flash_config;
            if (!flashConfig) {
                this.flashError = this.$t("tools.rnode_flasher.errors.no_flash_config");
                ToastUtils.error(this.flashError);
                return;
            }
            this.isFlashing = true;
            this.flashingProgress = 0;
            this.flashingStatus = this.$t("tools.rnode_flasher.connecting_device");
            let transport = null;
            try {
                transport = await SerialTransport.request();

                const blobReader = new window.zip.BlobReader(this.firmwareFile);
                const zipReader = new window.zip.ZipReader(blobReader);
                const zipEntries = await zipReader.getEntries();

                const filesToFlash = [];
                for (const [address, filename] of Object.entries(flashConfig.flash_files)) {
                    const entry = zipEntries.find((e) => e.filename === filename);
                    if (!entry) {
                        throw new Error(this.$t("tools.rnode_flasher.errors.failed_extract", { file: filename }));
                    }
                    const blob = await entry.getData(new window.zip.BlobWriter());
                    filesToFlash.push({
                        address: parseInt(address),
                        data: await this._readAsBinaryString(blob),
                    });
                }

                const espTransport = new window.Transport(transport.port, true);
                const esploader = new window.ESPLoader({
                    transport: espTransport,
                    baudrate: 921600,
                    terminal: { writeLine: console.log, write: console.log, clean: () => {} },
                });

                await esploader.main();
                await esploader.writeFlash({
                    fileArray: filesToFlash,
                    flashSize: flashConfig.flash_size,
                    flashMode: "DIO",
                    flashFreq: "80MHz",
                    calculateMD5Hash: (img) => window.CryptoJS.MD5(window.CryptoJS.enc.Latin1.parse(img)),
                    reportProgress: (idx, written, total) => {
                        this.flashingProgress = Math.floor((written / total) * 100);
                        this.flashingStatus = this.$t("tools.rnode_flasher.flashing_file_progress", {
                            current: idx + 1,
                            total: filesToFlash.length,
                            percentage: this.flashingProgress,
                        });
                    },
                });

                await espTransport.setDTR(false);
                await new Promise((r) => setTimeout(r, 100));
                await espTransport.setDTR(true);

                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.flash_success"));
            } catch (e) {
                this.flashError = this.$t("tools.rnode_flasher.errors.failed_flash", { error: e.message || e });
                ToastUtils.error(this.flashError);
            } finally {
                this.isFlashing = false;
                this.flashingStatus = "";
                if (transport) await transport.close().catch(() => {});
            }
        },
        async provision() {
            try {
                this.isProvisioning = true;
                await this._withRNode(async (rnode) => {
                    const rom = await rnode.getRomAsObject();
                    if (rom.parse()) {
                        ToastUtils.error(this.$t("tools.rnode_flasher.errors.provisioned_already"));
                        return;
                    }
                    if (!this.selectedProduct || !this.selectedModel) {
                        ToastUtils.error(this.$t("tools.rnode_flasher.errors.select_product_first"));
                        return;
                    }
                    const product = this.selectedProduct.id;
                    const model = this.selectedModel.mapped_id ?? this.selectedModel.id;
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
                    ToastUtils.success(this.$t("tools.rnode_flasher.alerts.provision_success"));
                });
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_provision", { error: e.message || e }));
            } finally {
                this.isProvisioning = false;
            }
        },
        async setFirmwareHash() {
            try {
                this.isSettingFirmwareHash = true;
                await this._withRNode(async (rnode) => {
                    const rom = await rnode.getRomAsObject();
                    if (!rom.parse()) {
                        ToastUtils.error(this.$t("tools.rnode_flasher.errors.not_provisioned"));
                        return;
                    }
                    const hash = await rnode.getFirmwareHash();
                    await rnode.setFirmwareHash(hash);
                    await RNodeUtils.sleepMillis(5000);
                    await rnode.reset().catch(() => {});
                    ToastUtils.success(this.$t("tools.rnode_flasher.alerts.hash_success"));
                });
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_set_hash", { error: e.message || e }));
            } finally {
                this.isSettingFirmwareHash = false;
            }
        },
        async enableTncMode() {
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.setFrequency(this.configFrequency);
                    await rnode.setBandwidth(this.configBandwidth);
                    await rnode.setTxPower(this.configTxPower);
                    await rnode.setSpreadingFactor(this.configSpreadingFactor);
                    await rnode.setCodingRate(this.configCodingRate);
                    await rnode.setRadioStateOn();
                    await RNodeUtils.sleepMillis(500);
                    await rnode.saveConfig();
                    await rnode.saveConfig();
                    await RNodeUtils.sleepMillis(5000);
                    await rnode.reset();
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.tnc_enabled"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_enable_tnc", { error: e.message || e }));
            }
        },
        async disableTncMode() {
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.deleteConfig();
                    await RNodeUtils.sleepMillis(5000);
                    await rnode.reset();
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.tnc_disabled"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_disable_tnc", { error: e.message || e }));
            }
        },
        async enableBluetooth() {
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.enableBluetooth();
                    await RNodeUtils.sleepMillis(1000);
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_enabled"));
            } catch (e) {
                ToastUtils.error(
                    this.$t("tools.rnode_flasher.errors.failed_enable_bluetooth", {
                        error: e.message || e,
                    })
                );
            }
        },
        async disableBluetooth() {
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.disableBluetooth();
                    await RNodeUtils.sleepMillis(1000);
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_disabled"));
            } catch (e) {
                ToastUtils.error(
                    this.$t("tools.rnode_flasher.errors.failed_disable_bluetooth", {
                        error: e.message || e,
                    })
                );
            }
        },
        async startBluetoothPairing() {
            try {
                await this._withRNode(async (rnode) => {
                    await rnode.startBluetoothPairing((pin) => {
                        ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_pairing_pin", { pin }));
                    });
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_pairing_started"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_start_pairing", { error: e.message || e }));
            }
        },
        async _readAsBinaryString(blob) {
            return new Promise((resolve) => {
                const r = new FileReader();
                r.onload = () => resolve(r.result);
                r.readAsBinaryString(blob);
            });
        },
        _displayBufferToPng(displayBuffer) {
            const displayArea = displayBuffer.slice(0, 512);
            const statArea = displayBuffer.slice(512, 1024);
            const displayCanvas = this._frameBufferToCanvas(displayArea, 64, 64, "#000000", "#FFFFFF");
            const statCanvas = this._frameBufferToCanvas(statArea, 64, 64, "#000000", "#FFFFFF");

            const canvas = document.createElement("canvas");
            canvas.width = 128;
            canvas.height = 64;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(displayCanvas, 0, 0);
            ctx.drawImage(statCanvas, 64, 0);

            const scaledCanvas = document.createElement("canvas");
            scaledCanvas.width = 512;
            scaledCanvas.height = 256;
            const sCtx = scaledCanvas.getContext("2d");
            sCtx.imageSmoothingEnabled = false;
            sCtx.drawImage(canvas, 0, 0, 512, 256);

            return scaledCanvas.toDataURL("image/png");
        },
        _frameBufferToCanvas(fb, w, h, bg, fg) {
            const c = document.createElement("canvas");
            c.width = w;
            c.height = h;
            const ctx = c.getContext("2d");
            ctx.fillStyle = bg;
            ctx.fillRect(0, 0, w, h);
            ctx.fillStyle = fg;
            for (let y = 0; y < h; y++) {
                for (let x = 0; x < w; x++) {
                    const idx = Math.floor((y * w + x) / 8);
                    const bit = (fb[idx] >> (7 - (x % 8))) & 1;
                    if (bit) ctx.fillRect(x, y, 1, 1);
                }
            }
            return c;
        },
    },
};
</script>
