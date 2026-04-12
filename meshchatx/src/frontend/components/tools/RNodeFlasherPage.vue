<template>
    <div class="flex flex-col h-full w-full bg-white dark:bg-zinc-950 overflow-hidden min-w-0">
        <!-- header -->
        <div
            class="flex flex-wrap items-center gap-2 px-3 sm:px-4 py-2 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 z-10 relative"
        >
            <div class="flex items-center gap-2 min-w-0 flex-1">
                <v-icon icon="mdi-chip" color="purple" size="24" class="shrink-0"></v-icon>
                <h1 class="text-lg sm:text-xl font-black text-gray-900 dark:text-white truncate">
                    {{ $t("tools.rnode_flasher.title") }}
                </h1>
            </div>

            <div class="ml-auto flex flex-wrap items-center justify-end gap-1 sm:gap-2 shrink-0">
                <button
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
                    @click="showAdvanced = !showAdvanced"
                >
                    <MaterialDesignIcon :icon-name="showAdvanced ? 'cog' : 'cog-outline'" class="size-5" />
                    <span class="hidden sm:inline">{{ showAdvanced ? "Simple" : "Advanced" }}</span>
                </button>
                <a
                    href="/rnode-flasher/index.html"
                    target="_blank"
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
                    title="Open original flasher in new tab"
                >
                    <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                    <span class="hidden sm:inline">Original</span>
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
        <div class="flex-1 min-h-0 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6">
            <!-- setup card: Select device & Firmware -->
            <div class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-lg overflow-hidden">
                <div class="grid grid-cols-1 md:grid-cols-2">
                    <!-- Left: Device Selection -->
                    <div class="p-6 border-b md:border-b-0 md:border-r border-gray-100 dark:border-zinc-800 space-y-4">
                        <div class="flex items-center gap-2 mb-2">
                            <div
                                class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400"
                            >
                                <MaterialDesignIcon icon-name="usb-port" class="size-5" />
                            </div>
                            <h2 class="font-bold text-gray-900 dark:text-zinc-100">
                                1. {{ $t("tools.rnode_flasher.select_device") }}
                            </h2>
                        </div>

                        <div class="space-y-3">
                            <div class="space-y-1">
                                <label
                                    class="text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                                    >{{ $t("tools.rnode_flasher.connection_method") }}</label
                                >
                                <div class="flex gap-2">
                                    <button
                                        class="flex-1 py-2 px-3 rounded-xl border text-sm font-bold transition-all"
                                        :class="
                                            connectionMethod === 'serial'
                                                ? 'bg-blue-600 text-white border-blue-600'
                                                : 'bg-gray-50 dark:bg-zinc-800/50 border-gray-200 dark:border-zinc-800 text-gray-700 dark:text-zinc-300'
                                        "
                                        @click="connectionMethod = 'serial'"
                                    >
                                        {{ $t("tools.rnode_flasher.serial") }}
                                    </button>
                                    <button
                                        class="flex-1 py-2 px-3 rounded-xl border text-sm font-bold transition-all"
                                        :class="
                                            connectionMethod === 'wifi'
                                                ? 'bg-blue-600 text-white border-blue-600'
                                                : 'bg-gray-50 dark:bg-zinc-800/50 border-gray-200 dark:border-zinc-800 text-gray-700 dark:text-zinc-300'
                                        "
                                        @click="connectionMethod = 'wifi'"
                                    >
                                        {{ $t("tools.rnode_flasher.wifi") }}
                                    </button>
                                </div>
                            </div>

                            <div v-if="connectionMethod === 'wifi'" class="space-y-1">
                                <label
                                    class="text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                                    >{{ $t("tools.rnode_flasher.ip_address") }}</label
                                >
                                <input
                                    v-model="wifiIpAddress"
                                    type="text"
                                    class="w-full bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all"
                                    :placeholder="$t('tools.rnode_flasher.ip_address_placeholder')"
                                />
                            </div>

                            <div class="space-y-1">
                                <label
                                    class="text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                                    >{{ $t("tools.rnode_flasher.product") }}</label
                                >
                                <select
                                    v-model="selectedProduct"
                                    class="w-full bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all"
                                >
                                    <option :value="null" disabled>
                                        {{ $t("tools.rnode_flasher.select_product") }}
                                    </option>
                                    <option v-for="product of products" :key="product.id" :value="product">
                                        {{ product.name }}
                                    </option>
                                </select>
                            </div>

                            <div class="space-y-1">
                                <label
                                    class="text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                                    >{{ $t("tools.rnode_flasher.model") }}</label
                                >
                                <select
                                    v-model="selectedModel"
                                    :disabled="!selectedProduct"
                                    class="w-full bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 transition-all disabled:opacity-50"
                                >
                                    <option :value="null" disabled>{{ $t("tools.rnode_flasher.select_model") }}</option>
                                    <template v-if="selectedProduct">
                                        <option v-for="model of selectedProduct.models" :key="model.id" :value="model">
                                            {{ model.name }}
                                        </option>
                                    </template>
                                </select>
                            </div>

                            <button
                                v-if="selectedProduct?.platform === 0x70"
                                :disabled="isEnteringDfuMode"
                                class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-amber-100 dark:bg-amber-900/30 hover:bg-amber-200 dark:hover:bg-amber-900/40 px-4 py-2.5 text-sm font-bold text-amber-700 dark:text-amber-400 transition-colors disabled:opacity-50"
                                @click="enterDfuMode"
                            >
                                <v-progress-circular v-if="isEnteringDfuMode" indeterminate size="16" width="2" />
                                <span>{{
                                    isEnteringDfuMode
                                        ? $t("tools.rnode_flasher.entering_dfu_mode")
                                        : $t("tools.rnode_flasher.enter_dfu_mode")
                                }}</span>
                            </button>
                        </div>
                    </div>

                    <!-- Right: Firmware Selection -->
                    <div class="p-6 space-y-4 bg-gray-50/50 dark:bg-zinc-900/50">
                        <div class="flex items-center gap-2 mb-2">
                            <div
                                class="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400"
                            >
                                <MaterialDesignIcon icon-name="file-download" class="size-5" />
                            </div>
                            <h2 class="font-bold text-gray-900 dark:text-zinc-100">
                                2. {{ $t("tools.rnode_flasher.select_firmware") }}
                            </h2>
                        </div>

                        <div class="space-y-4">
                            <!-- Auto-download section -->
                            <div
                                v-if="selectedProduct && selectedModel && recommendedFirmwareFilename"
                                class="p-4 rounded-xl border border-blue-100 dark:border-blue-900/30 bg-blue-50/50 dark:bg-blue-900/10 space-y-3"
                            >
                                <div class="text-xs font-bold text-blue-700 dark:text-blue-400 uppercase">
                                    {{ $t("tools.rnode_flasher.download_recommended") }}
                                </div>
                                <div class="text-sm text-gray-600 dark:text-zinc-400 break-all font-mono">
                                    {{ recommendedFirmwareFilename }}
                                </div>
                                <button
                                    :disabled="isDownloadingFirmware || !latestRelease"
                                    class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-700 px-4 py-2.5 text-sm font-bold text-white transition-colors disabled:opacity-50"
                                    @click="downloadRecommendedFirmware"
                                >
                                    <v-progress-circular
                                        v-if="isDownloadingFirmware"
                                        indeterminate
                                        size="16"
                                        width="2"
                                    />
                                    <MaterialDesignIcon v-else icon-name="cloud-download" class="size-4" />
                                    <span>{{
                                        isDownloadingFirmware
                                            ? $t("tools.rnode_flasher.downloading")
                                            : $t("tools.rnode_flasher.download_recommended")
                                    }}</span>
                                </button>
                            </div>

                            <!-- Manual file pick -->
                            <div class="space-y-1">
                                <label
                                    class="text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                                    >{{ $t("tools.rnode_flasher.select_firmware") }}</label
                                >
                                <input
                                    ref="file"
                                    type="file"
                                    accept=".zip"
                                    class="block w-full text-sm text-gray-900 dark:text-zinc-100 border border-gray-200 dark:border-zinc-800 rounded-xl cursor-pointer bg-white dark:bg-zinc-900 focus:outline-none file:mr-4 file:py-2.5 file:px-4 file:border-0 file:text-sm file:font-bold file:bg-zinc-200 dark:file:bg-zinc-700 file:text-zinc-700 dark:file:text-zinc-200 hover:file:bg-zinc-300 dark:hover:file:bg-zinc-600"
                                />
                            </div>

                            <div
                                v-if="flashError"
                                class="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-400"
                            >
                                {{ flashError }}
                            </div>

                            <button
                                :disabled="!selectedProduct || !selectedModel || isFlashing"
                                class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-green-600 hover:bg-green-700 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-green-600/20 transition-all active:scale-[0.98] disabled:opacity-50"
                                @click="flash"
                            >
                                <MaterialDesignIcon v-if="!isFlashing" icon-name="flash" class="size-5" />
                                <v-progress-circular v-else indeterminate size="16" width="2" />
                                <span>{{
                                    isFlashing
                                        ? $t("tools.rnode_flasher.flashing", { percentage: flashingProgress })
                                        : $t("tools.rnode_flasher.flash_now")
                                }}</span>
                            </button>

                            <div v-if="isFlashing" class="space-y-1.5 pt-2">
                                <v-progress-linear v-model="flashingProgress" color="green" height="8" rounded />
                                <div class="text-[10px] text-center text-gray-500 font-mono">{{ flashingStatus }}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- actions & tools card -->
            <div
                v-if="showAdvanced || isProvisioning || isSettingFirmwareHash"
                class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 rounded-lg p-4 sm:p-6 space-y-6"
            >
                <!-- Provision & Finalize -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="space-y-3">
                        <div class="flex items-center gap-2">
                            <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                                3. {{ $t("tools.rnode_flasher.step_provision") }}
                            </h3>
                            <MaterialDesignIcon icon-name="key-variant" class="size-4 text-zinc-400" />
                        </div>
                        <p class="text-xs text-gray-500 dark:text-zinc-500">
                            {{ $t("tools.rnode_flasher.provision_description") }}
                        </p>
                        <button
                            v-if="!isProvisioning"
                            :disabled="!selectedProduct || !selectedModel"
                            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/40 px-4 py-2.5 text-sm font-bold text-blue-700 dark:text-blue-400 transition-colors disabled:opacity-50"
                            @click="provision"
                        >
                            {{ $t("tools.rnode_flasher.provision") }}
                        </button>
                        <div v-else class="flex items-center justify-center gap-2 text-sm text-blue-600 p-2">
                            <v-progress-circular indeterminate size="18" width="2" />
                            <span class="font-bold">{{ $t("tools.rnode_flasher.provisioning_wait") }}</span>
                        </div>
                    </div>

                    <div class="space-y-3">
                        <div class="flex items-center gap-2">
                            <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                                4. {{ $t("tools.rnode_flasher.step_set_hash") }}
                            </h3>
                            <MaterialDesignIcon icon-name="shield-check" class="size-4 text-zinc-400" />
                        </div>
                        <p class="text-xs text-gray-500 dark:text-zinc-500">
                            {{ $t("tools.rnode_flasher.set_hash_description") }}
                        </p>
                        <button
                            v-if="!isSettingFirmwareHash"
                            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/40 px-4 py-2.5 text-sm font-bold text-blue-700 dark:text-blue-400 transition-colors"
                            @click="setFirmwareHash"
                        >
                            {{ $t("tools.rnode_flasher.set_firmware_hash") }}
                        </button>
                        <div v-else class="flex items-center justify-center gap-2 text-sm text-blue-600 p-2">
                            <v-progress-circular indeterminate size="18" width="2" />
                            <span class="font-bold">{{ $t("tools.rnode_flasher.setting_hash_wait") }}</span>
                        </div>
                    </div>
                </div>

                <!-- Advanced Actions Grid -->
                <div v-if="showAdvanced" class="pt-6 border-t border-gray-100 dark:border-zinc-800">
                    <div class="text-xs font-bold text-gray-400 dark:text-zinc-600 uppercase mb-4 tracking-widest">
                        {{ $t("tools.rnode_flasher.advanced_tools") }}
                    </div>
                    <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
                        <button class="action-btn" @click="detect">
                            <MaterialDesignIcon icon-name="magnify" class="size-4" />
                            <span>{{ $t("tools.rnode_flasher.detect_rnode") }}</span>
                        </button>
                        <button class="action-btn" @click="reboot">
                            <MaterialDesignIcon icon-name="restart" class="size-4" />
                            <span>{{ $t("tools.rnode_flasher.reboot_rnode") }}</span>
                        </button>
                        <button class="action-btn" @click="readDisplay">
                            <MaterialDesignIcon icon-name="monitor" class="size-4" />
                            <span>{{ $t("tools.rnode_flasher.read_display") }}</span>
                        </button>
                        <button class="action-btn" @click="dumpEeprom">
                            <MaterialDesignIcon icon-name="database-export" class="size-4" />
                            <span>{{ $t("tools.rnode_flasher.dump_eeprom") }}</span>
                        </button>
                        <button class="action-btn danger" @click="wipeEeprom">
                            <MaterialDesignIcon icon-name="eraser" class="size-4" />
                            <span>{{ $t("tools.rnode_flasher.wipe_eeprom") }}</span>
                        </button>
                    </div>

                    <div
                        v-if="rnodeDisplayImage"
                        class="mt-4 p-4 rounded-2xl bg-zinc-950 flex justify-center border border-zinc-800"
                    >
                        <img :src="rnodeDisplayImage" class="h-28 pixelated" />
                    </div>
                </div>
            </div>

            <!-- config cards -->
            <div v-if="showAdvanced" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- Bluetooth -->
                <div
                    class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl shadow-xl overflow-hidden"
                >
                    <div class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center gap-2">
                        <MaterialDesignIcon icon-name="bluetooth" class="size-5 text-blue-500" />
                        <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                            {{ $t("tools.rnode_flasher.configure_bluetooth") }}
                        </h3>
                    </div>
                    <div class="p-6 space-y-4">
                        <div class="flex flex-wrap gap-2">
                            <button class="action-btn flex-1" @click="enableBluetooth">
                                {{ $t("tools.rnode_flasher.enable") }}
                            </button>
                            <button class="action-btn flex-1" @click="disableBluetooth">
                                {{ $t("tools.rnode_flasher.disable") }}
                            </button>
                            <button
                                class="action-btn flex-[2] bg-blue-500 !text-white !border-none"
                                @click="startBluetoothPairing"
                            >
                                {{ $t("tools.rnode_flasher.start_pairing") }}
                            </button>
                        </div>
                        <div
                            class="text-[10px] text-gray-400 dark:text-zinc-500 leading-relaxed uppercase tracking-wider"
                        >
                            {{ $t("tools.rnode_flasher.bluetooth_restart_warning") }}
                        </div>
                    </div>
                </div>

                <!-- TNC -->
                <div
                    class="border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl shadow-xl overflow-hidden"
                >
                    <div class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center gap-2">
                        <MaterialDesignIcon icon-name="radio-tower" class="size-5 text-green-500" />
                        <h3 class="font-bold text-gray-900 dark:text-zinc-100">
                            {{ $t("tools.rnode_flasher.configure_tnc") }}
                        </h3>
                    </div>
                    <div class="p-6 space-y-4">
                        <div class="grid grid-cols-2 gap-3">
                            <div class="space-y-1">
                                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{
                                    $t("tools.rnode_flasher.frequency")
                                }}</label>
                                <input v-model="configFrequency" type="number" class="config-input" />
                            </div>
                            <div class="space-y-1">
                                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{
                                    $t("tools.rnode_flasher.tx_power")
                                }}</label>
                                <input v-model="configTxPower" type="number" class="config-input" />
                            </div>
                            <div class="space-y-1">
                                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{
                                    $t("tools.rnode_flasher.bandwidth")
                                }}</label>
                                <select v-model="configBandwidth" class="config-input">
                                    <option v-for="bw in RNodeInterfaceDefaults.bandwidths" :key="bw" :value="bw">
                                        {{ bw / 1000 }} KHz
                                    </option>
                                </select>
                            </div>
                            <div class="space-y-1">
                                <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{
                                    $t("tools.rnode_flasher.spreading_factor")
                                }}</label>
                                <select v-model="configSpreadingFactor" class="config-input">
                                    <option v-for="sf in RNodeInterfaceDefaults.spreadingfactors" :key="sf" :value="sf">
                                        {{ sf }}
                                    </option>
                                </select>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button
                                class="action-btn flex-1 bg-green-600 !text-white !border-none"
                                @click="enableTncMode"
                            >
                                {{ $t("tools.rnode_flasher.enable") }}
                            </button>
                            <button class="action-btn flex-1" @click="disableTncMode">
                                {{ $t("tools.rnode_flasher.disable") }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- help footer -->
            <div
                class="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-zinc-50 dark:bg-zinc-900/30"
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
import RNode from "../../js/rnode/RNode.js";
import ROM from "../../js/rnode/ROM.js";
import Nrf52DfuFlasher from "../../js/rnode/Nrf52DfuFlasher.js";
import RNodeUtils from "../../js/rnode/RNodeUtils.js";
import products from "../../js/rnode/products.js";
import ToastUtils from "../../js/ToastUtils.js";
import GlobalState from "../../js/GlobalState";

export default {
    name: "RNodeFlasherPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            rnode: null,
            isFlashing: false,
            flashingProgress: 0,
            flashingStatus: "",
            flashError: null,
            isProvisioning: false,
            isSettingFirmwareHash: false,
            isEnteringDfuMode: false,
            rnodeDisplayImage: null,
            showAdvanced: false,
            connectionMethod: "serial",
            wifiIpAddress: "",
            selectedProduct: null,
            selectedModel: null,
            products: products,
            configFrequency: 917375000,
            configBandwidth: 250000,
            configTxPower: 22,
            configSpreadingFactor: 11,
            configCodingRate: 5,
            latestRelease: null,
            isDownloadingFirmware: false,
            RNodeInterfaceDefaults: {
                bandwidths: [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000],
                codingrates: [5, 6, 7, 8],
                spreadingfactors: [7, 8, 9, 10, 11, 12],
            },
        };
    },
    computed: {
        recommendedFirmwareFilename() {
            return this.selectedModel?.firmware_filename ?? this.selectedProduct?.firmware_filename;
        },
        giteaBaseUrl() {
            return GlobalState.config?.gitea_base_url || "https://git.quad4.io";
        },
    },
    watch: {
        selectedProduct() {
            this.selectedModel = null;
        },
    },
    mounted() {
        this.loadVendorLibraries();
        this.fetchLatestRelease();
    },
    methods: {
        async fetchLatestRelease() {
            try {
                const response = await fetch(
                    `${this.giteaBaseUrl}/api/v1/repos/Reticulum/RNode_Firmware/releases/latest`
                );
                if (response.ok) {
                    this.latestRelease = await response.json();
                }
            } catch {
                // ignore
            }
        },
        async downloadRecommendedFirmware() {
            if (!this.recommendedFirmwareFilename || !this.latestRelease) return;

            const asset = this.latestRelease.assets.find((a) => a.name === this.recommendedFirmwareFilename);
            if (!asset) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.firmware_not_found_in_release"));
                return;
            }

            this.isDownloadingFirmware = true;
            try {
                const downloadUrl = `/api/v1/tools/rnode/download_firmware?url=${encodeURIComponent(asset.browser_download_url)}`;
                const response = await fetch(downloadUrl);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: response.statusText }));
                    throw new Error(errorData.error || `Download failed with status ${response.status}`);
                }
                const blob = await response.blob();
                const file = new File([blob], asset.name, { type: "application/zip" });

                // Manually set the file to the input ref
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                this.$refs["file"].files = dataTransfer.files;

                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.firmware_downloaded"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_download", { error: e.message || e }));
            } finally {
                this.isDownloadingFirmware = false;
            }
        },
        async loadVendorLibraries() {
            // Check if libraries are already loaded
            if (window.zip && window.CryptoJS && window.ESPLoader) return;

            const libs = [
                "/rnode-flasher/js/zip.min.js",
                "/rnode-flasher/js/crypto-js@3.9.1-1/core.js",
                "/rnode-flasher/js/crypto-js@3.9.1-1/md5.js",
            ];

            for (const lib of libs) {
                await this.loadScript(lib);
            }

            try {
                // Load ES Modules
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

            // Setup polyfill
            if (!navigator.serial && navigator.usb && window.serial) {
                navigator.serial = window.serial;
            }
        },
        loadScript(src) {
            return new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.src = src;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        },
        async askForSerialPort() {
            if (!navigator.serial) {
                this.flashError = this.$t("tools.rnode_flasher.errors.web_serial_not_supported");
                ToastUtils.error(this.flashError);
                return null;
            }

            if (this.rnode) {
                try {
                    await this.rnode.close();
                } catch {
                    // ignore
                }
                this.rnode = null;
            }

            try {
                return await navigator.serial.requestPort({ filters: [] });
            } catch (e) {
                if (e.name === "NotFoundError" || e.message?.includes("No port selected")) {
                    this.flashError = this.$t("tools.rnode_flasher.errors.no_device_selected");
                } else {
                    this.flashError = this.$t("tools.rnode_flasher.errors.failed_connect", { error: e.message || e });
                }
                throw e;
            }
        },
        async askForRNode() {
            try {
                const serialPort = await this.askForSerialPort();
                if (!serialPort) return false;

                this.flashingStatus = this.$t("tools.rnode_flasher.connecting_device");
                this.rnode = await RNode.fromSerialPort(serialPort);
                const isRNode = await this.rnode.detect();
                if (!isRNode) {
                    await this.rnode.close();
                    this.flashError = this.$t("tools.rnode_flasher.errors.not_an_rnode");
                    ToastUtils.error(this.flashError);
                    this.flashingStatus = "";
                    return false;
                }

                this.flashingStatus = "";
                return this.rnode;
            } catch (e) {
                this.flashingStatus = "";
                throw e;
            }
        },
        async enterDfuMode() {
            this.isEnteringDfuMode = true;
            this.flashError = null;

            try {
                const serialPort = await this.askForSerialPort();
                if (!serialPort) return;

                const flasher = new Nrf52DfuFlasher(serialPort);
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
            if (this.connectionMethod === "wifi") {
                await this.flashWifi();
                return;
            }

            switch (this.selectedProduct?.platform) {
                case ROM.PLATFORM_ESP32:
                    await this.flashEsp32();
                    break;
                case ROM.PLATFORM_NRF52:
                    await this.flashNrf52();
                    break;
                default:
                    ToastUtils.error(this.$t("tools.rnode_flasher.errors.select_product_first"));
                    break;
            }
        },
        async flashWifi() {
            this.flashError = null;
            const file = this.$refs["file"].files[0];
            if (!file) {
                this.flashError = this.$t("tools.rnode_flasher.errors.select_firmware_first");
                ToastUtils.error(this.flashError);
                return;
            }

            if (!this.wifiIpAddress) {
                this.flashError = "Please enter an IP address";
                ToastUtils.error(this.flashError);
                return;
            }

            this.isFlashing = true;
            this.flashingProgress = 0;
            this.flashingStatus = "Preparing firmware for WiFi upload...";

            try {
                const blobReader = new window.zip.BlobReader(file);
                const zipReader = new window.zip.ZipReader(blobReader);
                const zipEntries = await zipReader.getEntries();

                // Find the main .bin file (usually the one at 0x10000 in flash_config)
                const flashConfig = this.selectedModel?.flash_config ?? this.selectedProduct?.flash_config;
                let mainBinFilename = null;
                if (flashConfig && flashConfig.flash_files) {
                    mainBinFilename = flashConfig.flash_files["0x10000"];
                }

                // fallback: find any .bin file that isn't bootloader or partitions if flash_config is missing
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
                    throw new Error("Could not find main firmware .bin in ZIP file.");
                }

                const entry = zipEntries.find((e) => e.filename === mainBinFilename);
                if (!entry) throw new Error(`Firmware file ${mainBinFilename} not found in ZIP.`);

                const binBlob = await entry.getData(new window.zip.BlobWriter());

                this.flashingStatus = `Uploading ${mainBinFilename} to ${this.wifiIpAddress}...`;

                await this.uploadOta(this.wifiIpAddress, binBlob);

                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.flash_success"));
            } catch (e) {
                this.flashError = this.$t("tools.rnode_flasher.errors.failed_ota", { error: e.message || e });
                ToastUtils.error(this.flashError);
            } finally {
                this.isFlashing = false;
                this.flashingStatus = "";
            }
        },
        async uploadOta(ip, blob) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                // We use http here because devices usually don't have https
                xhr.open("POST", `http://${ip}/update`, true);

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        this.flashingProgress = Math.floor((e.loaded / e.total) * 100);
                        this.flashingStatus = `Uploading: ${this.flashingProgress}%`;
                    }
                };

                xhr.onload = () => {
                    if (xhr.status === 200) {
                        resolve();
                    } else {
                        reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`));
                    }
                };

                xhr.onerror = () =>
                    reject(
                        new Error(
                            "Network error occurred during upload. Check if IP is correct and device is reachable."
                        )
                    );

                const formData = new FormData();
                formData.append("update", blob, "firmware.bin");
                xhr.send(formData);
            });
        },
        async flashNrf52() {
            this.flashError = null;
            const file = this.$refs["file"].files[0];
            if (!file) {
                this.flashError = this.$t("tools.rnode_flasher.errors.select_firmware_first");
                ToastUtils.error(this.flashError);
                return;
            }

            let serialPort = null;
            try {
                serialPort = await this.askForSerialPort();
                if (!serialPort) return;

                this.isFlashing = true;
                this.flashingProgress = 0;
                this.flashingStatus = this.$t("tools.rnode_flasher.connecting_device");

                const flasher = new Nrf52DfuFlasher(serialPort);
                await flasher.flash(file, (percentage, message) => {
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
                if (serialPort) await serialPort.close().catch(() => {});
            }
        },
        async flashEsp32() {
            this.flashError = null;
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

            const file = this.$refs["file"].files[0];
            if (!file) {
                this.flashError = this.$t("tools.rnode_flasher.errors.select_firmware_first");
                ToastUtils.error(this.flashError);
                return;
            }

            let serialPort = null;
            try {
                serialPort = await this.askForSerialPort();
                if (!serialPort) return;

                this.isFlashing = true;
                this.flashingProgress = 0;
                this.flashingStatus = this.$t("tools.rnode_flasher.connecting_device");

                const blobReader = new window.zip.BlobReader(file);
                const zipReader = new window.zip.ZipReader(blobReader);
                const zipEntries = await zipReader.getEntries();

                const filesToFlash = [];
                for (const [address, filename] of Object.entries(flashConfig.flash_files)) {
                    const entry = zipEntries.find((e) => e.filename === filename);
                    if (!entry)
                        throw new Error(this.$t("tools.rnode_flasher.errors.failed_extract", { file: filename }));
                    const blob = await entry.getData(new window.zip.BlobWriter());
                    filesToFlash.push({
                        address: parseInt(address),
                        data: await this.readAsBinaryString(blob),
                    });
                }

                const transport = new window.Transport(serialPort, true);
                const esploader = new window.ESPLoader({
                    transport,
                    baudrate: 921600,
                    terminal: {
                        writeLine: console.log,
                        write: console.log,
                        clean: () => {},
                    },
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

                // Reboot
                await transport.setDTR(false);
                await new Promise((r) => setTimeout(r, 100));
                await transport.setDTR(true);

                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.flash_success"));
            } catch (e) {
                this.flashError = this.$t("tools.rnode_flasher.errors.failed_flash", { error: e.message || e });
                ToastUtils.error(this.flashError);
            } finally {
                this.isFlashing = false;
                this.flashingStatus = "";
                if (serialPort) await serialPort.close().catch(() => {});
            }
        },
        async detect() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                const ver = await rnode.getFirmwareVersion();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.rnode_detected", { version: ver }));
                await rnode.close();
            } catch {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_detect"));
            }
        },
        async reboot() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.reset();
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.rebooting"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_reboot", { error: e.message || e }));
            }
        },
        async readDisplay() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                const buffer = await rnode.readDisplay();
                await rnode.close();
                this.rnodeDisplayImage = this.rnodeDisplayBufferToPng(buffer);
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_read_display", { error: e.message || e }));
            }
        },
        rnodeDisplayBufferToPng(displayBuffer) {
            const displayArea = displayBuffer.slice(0, 512);
            const statArea = displayBuffer.slice(512, 1024);

            const displayCanvas = this.frameBufferToCanvas(displayArea, 64, 64, "#000000", "#FFFFFF");
            const statCanvas = this.frameBufferToCanvas(statArea, 64, 64, "#000000", "#FFFFFF");

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
        frameBufferToCanvas(fb, w, h, bg, fg) {
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
        async dumpEeprom() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                const eeprom = await rnode.getRom();
                console.log(RNodeUtils.bytesToHex(eeprom));
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.eeprom_dumped"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_dump_eeprom", { error: e.message || e }));
            }
        },
        async wipeEeprom() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                if (!confirm(this.$t("tools.rnode_flasher.alerts.eeprom_wipe_confirm"))) {
                    await rnode.close();
                    return;
                }
                await rnode.wipeRom();
                await rnode.reset();
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.eeprom_wiped"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_wipe_eeprom", { error: e.message || e }));
            }
        },
        async provision() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                const rom = await rnode.getRomAsObject();
                if (rom.parse()) {
                    ToastUtils.error(this.$t("tools.rnode_flasher.errors.provisioned_already"));
                    await rnode.close();
                    return;
                }
                if (!this.selectedProduct || !this.selectedModel) {
                    ToastUtils.error(this.$t("tools.rnode_flasher.errors.select_product_first"));
                    await rnode.close();
                    return;
                }

                this.isProvisioning = true;
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
                await rnode.writeRom(ROM.ADDR_SERIAL, sBytes[0]);
                await rnode.writeRom(ROM.ADDR_SERIAL + 1, sBytes[1]);
                await rnode.writeRom(ROM.ADDR_SERIAL + 2, sBytes[2]);
                await rnode.writeRom(ROM.ADDR_SERIAL + 3, sBytes[3]);
                await rnode.writeRom(ROM.ADDR_MADE, tBytes[0]);
                await rnode.writeRom(ROM.ADDR_MADE + 1, tBytes[1]);
                await rnode.writeRom(ROM.ADDR_MADE + 2, tBytes[2]);
                await rnode.writeRom(ROM.ADDR_MADE + 3, tBytes[3]);

                for (let i = 0; i < 16; i++) await rnode.writeRom(ROM.ADDR_CHKSUM + i, checksum[i]);
                for (let i = 0; i < 128; i++) await rnode.writeRom(ROM.ADDR_SIGNATURE + i, 0x00);
                await rnode.writeRom(ROM.ADDR_INFO_LOCK, ROM.INFO_LOCK_BYTE);

                await RNodeUtils.sleepMillis(5000);
                await rnode.reset();
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.provision_success"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_provision", { error: e.message || e }));
            } finally {
                this.isProvisioning = false;
            }
        },
        async setFirmwareHash() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                const rom = await rnode.getRomAsObject();
                if (!rom.parse()) {
                    ToastUtils.error(this.$t("tools.rnode_flasher.errors.not_provisioned"));
                    await rnode.close();
                    return;
                }
                this.isSettingFirmwareHash = true;
                const hash = await rnode.getFirmwareHash();
                await rnode.setFirmwareHash(hash);
                await RNodeUtils.sleepMillis(5000);
                await rnode.reset().catch(() => {
                    // ignore
                });
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.hash_success"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_set_hash", { error: e.message || e }));
            } finally {
                this.isSettingFirmwareHash = false;
            }
        },
        async enableTncMode() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
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
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.tnc_enabled"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_enable_tnc", { error: e.message || e }));
            }
        },
        async disableTncMode() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.deleteConfig();
                await RNodeUtils.sleepMillis(5000);
                await rnode.reset();
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.tnc_disabled"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_disable_tnc", { error: e.message || e }));
            }
        },
        async enableBluetooth() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.enableBluetooth();
                await RNodeUtils.sleepMillis(1000);
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_enabled"));
            } catch (e) {
                ToastUtils.error(
                    this.$t("tools.rnode_flasher.errors.failed_enable_bluetooth", { error: e.message || e })
                );
            }
        },
        async disableBluetooth() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.disableBluetooth();
                await RNodeUtils.sleepMillis(1000);
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_disabled"));
            } catch (e) {
                ToastUtils.error(
                    this.$t("tools.rnode_flasher.errors.failed_disable_bluetooth", { error: e.message || e })
                );
            }
        },
        async startBluetoothPairing() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.startBluetoothPairing((pin) => {
                    ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_pairing_pin", { pin }));
                });
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.bluetooth_pairing_started"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_start_pairing", { error: e.message || e }));
            }
        },
        async setDisplayRotation(rot) {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.setDisplayRotation(rot);
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.rotation_updated"));
            } catch (e) {
                ToastUtils.error(this.$t("tools.rnode_flasher.errors.failed_set_rotation", { error: e.message || e }));
            }
        },
        async startDisplayReconditioning() {
            try {
                const rnode = await this.askForRNode();
                if (!rnode) return;
                await rnode.startDisplayReconditioning();
                await rnode.close();
                ToastUtils.success(this.$t("tools.rnode_flasher.alerts.reconditioning_started"));
            } catch (e) {
                ToastUtils.error(
                    this.$t("tools.rnode_flasher.errors.failed_start_reconditioning", { error: e.message || e })
                );
            }
        },
        async readAsBinaryString(blob) {
            return new Promise((resolve) => {
                const r = new FileReader();
                r.onload = () => resolve(r.result);
                r.readAsBinaryString(blob);
            });
        },
    },
};
</script>

<style scoped>
.action-btn {
    @apply inline-flex items-center justify-center gap-2 rounded-xl bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 px-3 py-2 text-[11px] font-bold text-gray-700 dark:text-zinc-300 border border-gray-200 dark:border-zinc-700 transition-all active:scale-95;
}

.action-btn.danger {
    @apply bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-100 dark:border-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/40;
}

.config-input {
    @apply w-full bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-[11px] rounded-lg focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500 px-3 py-2 transition-all;
}

.pixelated {
    image-rendering: pixelated;
}

select {
    appearance: none;
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
    background-position: right 0.5rem center;
    background-repeat: no-repeat;
    background-size: 1.5em 1.5em;
}

input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
</style>
