<template>
    <div
        class="interface-card transition-all duration-300"
        :class="{
            'opacity-60 grayscale-[0.5]': !isInterfaceEnabled(iface) || iface._restart_required || !isReticulumRunning,
        }"
    >
        <div class="flex gap-4 items-start relative">
            <!-- Offline Overlay -->
            <div
                v-if="!isReticulumRunning"
                class="absolute inset-0 z-10 flex items-center justify-center bg-white/40 dark:bg-zinc-900/40 backdrop-blur-[1px] rounded-3xl"
            >
                <div
                    class="bg-red-500 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-sm font-bold"
                >
                    <MaterialDesignIcon icon-name="lan-disconnect" class="w-4 h-4" />
                    <span>Reticulum Offline</span>
                </div>
            </div>

            <!-- Restart Required Overlay -->
            <div
                v-if="isReticulumRunning && iface._restart_required"
                class="absolute inset-0 z-10 flex items-center justify-center bg-white/40 dark:bg-zinc-900/40 backdrop-blur-[1px] rounded-3xl"
            >
                <div
                    class="bg-amber-500 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-sm font-bold animate-pulse"
                >
                    <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                    <span>{{ $t("interfaces.restart_required") }}</span>
                </div>
            </div>

            <div class="interface-card__icon">
                <MaterialDesignIcon :icon-name="iconName" class="w-6 h-6" />
            </div>
            <div class="flex-1 space-y-2">
                <div class="flex items-center gap-2 flex-wrap">
                    <div class="text-lg font-semibold text-gray-900 dark:text-white truncate">{{ iface._name }}</div>
                    <span class="type-chip">{{ iface.type }}</span>
                    <span :class="statusChipClass">{{
                        isInterfaceEnabled(iface) ? $t("app.enabled") : $t("app.disabled")
                    }}</span>
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-300">
                    {{ description }}
                </div>
                <div class="flex flex-wrap gap-2 text-xs text-gray-600 dark:text-gray-300">
                    <span v-if="iface._stats?.bitrate" class="stat-chip"
                        >{{ $t("interface.bitrate") }} {{ formatBitsPerSecond(iface._stats?.bitrate ?? 0) }}</span
                    >
                    <span class="stat-chip">{{ $t("interface.tx") }} {{ formatBytes(iface._stats?.txb ?? 0) }}</span>
                    <span class="stat-chip">{{ $t("interface.rx") }} {{ formatBytes(iface._stats?.rxb ?? 0) }}</span>
                    <span v-if="iface.type === 'RNodeInterface' && iface._stats?.noise_floor" class="stat-chip"
                        >{{ $t("interface.noise") }} {{ iface._stats?.noise_floor }} dBm</span
                    >
                    <span v-if="iface._stats?.clients != null" class="stat-chip"
                        >{{ $t("interface.clients") }} {{ iface._stats?.clients }}</span
                    >
                </div>
                <div v-if="iface._stats?.ifac_signature" class="ifac-line">
                    <span class="text-emerald-500 font-semibold">{{ iface._stats.ifac_size * 8 }}-bit IFAC</span>
                    <span v-if="iface._stats?.ifac_netname">• {{ iface._stats.ifac_netname }}</span>
                    <span>•</span>
                    <button
                        type="button"
                        class="text-blue-500 hover:underline"
                        @click="onIFACSignatureClick(iface._stats.ifac_signature)"
                    >
                        {{ iface._stats.ifac_signature.slice(0, 8) }}…{{ iface._stats.ifac_signature.slice(-8) }}
                    </button>
                </div>
            </div>
            <div class="flex flex-col gap-2 items-end relative">
                <button
                    v-if="isInterfaceEnabled(iface)"
                    type="button"
                    class="secondary-chip text-xs"
                    @click="disableInterface"
                >
                    <MaterialDesignIcon icon-name="power" class="w-4 h-4" />
                    {{ $t("interface.disable") }}
                </button>
                <button v-else type="button" class="primary-chip text-xs" @click="enableInterface">
                    <MaterialDesignIcon icon-name="power" class="w-4 h-4" />
                    {{ $t("interface.enable") }}
                </button>
                <div class="relative z-50">
                    <DropDownMenu>
                        <template #button>
                            <IconButton>
                                <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                            </IconButton>
                        </template>
                        <template #items>
                            <div class="max-h-60 overflow-auto py-1 space-y-1">
                                <DropDownMenuItem @click="editInterface">
                                    <MaterialDesignIcon icon-name="pencil" class="w-5 h-5" />
                                    <span>{{ $t("interface.edit_interface") }}</span>
                                </DropDownMenuItem>
                                <DropDownMenuItem @click="exportInterface">
                                    <MaterialDesignIcon icon-name="export" class="w-5 h-5" />
                                    <span>{{ $t("interface.export_interface") }}</span>
                                </DropDownMenuItem>
                                <DropDownMenuItem @click="deleteInterface">
                                    <MaterialDesignIcon icon-name="trash-can" class="w-5 h-5 text-red-500" />
                                    <span class="text-red-500">{{ $t("interface.delete_interface") }}</span>
                                </DropDownMenuItem>
                            </div>
                        </template>
                    </DropDownMenu>
                </div>
            </div>
        </div>

        <div
            v-if="['UDPInterface', 'RNodeInterface'].includes(iface.type)"
            class="mt-4 grid gap-2 text-sm text-gray-700 dark:text-gray-300"
        >
            <div v-if="iface.type === 'UDPInterface'" class="detail-grid">
                <div>
                    <div class="detail-label">{{ $t("interface.listen") }}</div>
                    <div class="detail-value">{{ iface.listen_ip }}:{{ iface.listen_port }}</div>
                </div>
                <div>
                    <div class="detail-label">{{ $t("interface.forward") }}</div>
                    <div class="detail-value">{{ iface.forward_ip }}:{{ iface.forward_port }}</div>
                </div>
            </div>
            <div v-else-if="iface.type === 'RNodeInterface'" class="detail-grid">
                <div>
                    <div class="detail-label">{{ $t("interface.port") }}</div>
                    <div class="detail-value">{{ iface.port }}</div>
                </div>
                <div>
                    <div class="detail-label">{{ $t("interface.frequency") }}</div>
                    <div class="detail-value">{{ formatFrequency(iface.frequency) }}</div>
                </div>
                <div>
                    <div class="detail-label">{{ $t("interface.bandwidth") }}</div>
                    <div class="detail-value">{{ formatFrequency(iface.bandwidth) }}</div>
                </div>
                <div>
                    <div class="detail-label">{{ $t("interface.spreading_factor") }}</div>
                    <div class="detail-value">{{ iface.spreadingfactor }}</div>
                </div>
                <div>
                    <div class="detail-label">{{ $t("interface.coding_rate") }}</div>
                    <div class="detail-value">{{ iface.codingrate }}</div>
                </div>
                <div>
                    <div class="detail-label">{{ $t("interface.txpower") }}</div>
                    <div class="detail-value">{{ iface.txpower }} dBm</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import Utils from "../../js/Utils";
import DropDownMenuItem from "../DropDownMenuItem.vue";
import IconButton from "../IconButton.vue";
import DropDownMenu from "../DropDownMenu.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "Interface",
    components: {
        DropDownMenu,
        IconButton,
        DropDownMenuItem,
        MaterialDesignIcon,
    },
    props: {
        iface: {
            type: Object,
            required: true,
        },
        isReticulumRunning: {
            type: Boolean,
            default: true,
        },
    },
    emits: ["enable", "disable", "edit", "export", "delete"],
    data() {
        return {};
    },
    computed: {
        iconName() {
            switch (this.iface.type) {
                case "AutoInterface":
                    return "home-automation";
                case "RNodeInterface":
                    return this.iface.port && this.iface.port.startsWith("tcp://") ? "lan-connect" : "radio-tower";
                case "RNodeMultiInterface":
                    return "access-point-network";
                case "TCPClientInterface":
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
        description() {
            if (this.iface.type === "TCPClientInterface") {
                return `${this.iface.target_host}:${this.iface.target_port}`;
            }
            if (this.iface.type === "TCPServerInterface" || this.iface.type === "UDPInterface") {
                return `${this.iface.listen_ip}:${this.iface.listen_port}`;
            }
            if (this.iface.type === "SerialInterface") {
                return `${this.iface.port} @ ${this.iface.speed || "9600"}bps`;
            }
            if (this.iface.type === "RNodeInterface" && this.iface.port && this.iface.port.startsWith("tcp://")) {
                return `RNode over IP @ ${this.iface.port.replace("tcp://", "")}`;
            }
            if (this.iface.type === "AutoInterface") {
                return "Auto-detect Ethernet and Wi-Fi peers";
            }
            return this.iface.description || "Custom interface";
        },
        statusChipClass() {
            return this.isInterfaceEnabled(this.iface)
                ? "inline-flex items-center rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-semibold"
                : "inline-flex items-center rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-semibold";
        },
    },
    methods: {
        onIFACSignatureClick: function (ifacSignature) {
            DialogUtils.alert(ifacSignature);
        },
        isInterfaceEnabled: function (iface) {
            return Utils.isInterfaceEnabled(iface);
        },
        enableInterface() {
            this.$emit("enable");
        },
        disableInterface() {
            this.$emit("disable");
        },
        editInterface() {
            this.$emit("edit");
        },
        exportInterface() {
            this.$emit("export");
        },
        deleteInterface() {
            this.$emit("delete");
        },
        formatBitsPerSecond: function (bits) {
            return Utils.formatBitsPerSecond(bits);
        },
        formatBytes: function (bytes) {
            return Utils.formatBytes(bytes);
        },
        formatFrequency(hz) {
            return Utils.formatFrequency(hz);
        },
    },
};
</script>

<style scoped>
.interface-card {
    @apply relative bg-white/95 dark:bg-zinc-900/85 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-lg p-4 space-y-3 hover:z-10;
    overflow: visible;
}
.interface-card__icon {
    @apply w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-900/40 dark:text-blue-200 flex items-center justify-center;
}
.type-chip {
    @apply inline-flex items-center rounded-full bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 text-xs font-semibold text-gray-600 dark:text-gray-200;
}
.stat-chip {
    @apply inline-flex items-center rounded-full border border-gray-200 dark:border-zinc-700 px-2 py-0.5;
}
.ifac-line {
    @apply text-xs flex flex-wrap items-center gap-1;
}
.detail-grid {
    @apply grid gap-3 sm:grid-cols-2;
}
.detail-label {
    @apply text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400;
}
.detail-value {
    @apply text-sm font-medium text-gray-900 dark:text-white;
}
</style>
