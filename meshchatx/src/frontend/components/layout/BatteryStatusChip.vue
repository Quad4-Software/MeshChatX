<template>
    <button
        v-if="visible"
        type="button"
        class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold tabular-nums transition-colors"
        :class="chipClass"
        :title="titleText"
        :aria-label="titleText"
        @click="onClick"
    >
        <MaterialDesignIcon :icon-name="iconName" class="h-4 w-4 shrink-0" />
        <span>{{ levelLabel }}</span>
    </button>
</template>

<script>
// SPDX-License-Identifier: 0BSD

import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { batteryStatusIconName, getDeviceBatteryStatus, shouldShowBatteryChip } from "../../js/deviceBattery.js";

const POLL_MS = 60000;

export default {
    name: "BatteryStatusChip",
    components: {
        MaterialDesignIcon,
    },
    emits: ["open-about"],
    data() {
        return {
            status: null,
            pollTimer: null,
            webBattery: null,
        };
    },
    computed: {
        visible() {
            return shouldShowBatteryChip(this.status);
        },
        iconName() {
            return batteryStatusIconName(this.status);
        },
        levelLabel() {
            if (this.status?.level == null) {
                return "";
            }
            return `${this.status.level}%`;
        },
        titleText() {
            if (!this.status?.supported) {
                return this.$t("app.battery_unavailable");
            }
            const level = this.status.level != null ? `${this.status.level}%` : this.$t("about.path_unknown");
            if (this.status.charging === true) {
                return this.$t("app.battery_charging_title", { percent: level });
            }
            if (this.status.charging === false) {
                return this.$t("app.battery_discharging_title", { percent: level });
            }
            return this.$t("app.battery_level_title", { percent: level });
        },
        chipClass() {
            const level = this.status?.level;
            if (this.status?.charging) {
                return "text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/40";
            }
            if (level != null && level <= 15) {
                return "text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/40";
            }
            if (level != null && level <= 30) {
                return "text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/40";
            }
            return "text-gray-700 dark:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800";
        },
    },
    mounted() {
        this.refresh();
        this.pollTimer = setInterval(() => {
            this.refresh();
        }, POLL_MS);
    },
    beforeUnmount() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        this.detachWebBatteryListeners();
    },
    methods: {
        onClick() {
            this.$emit("open-about");
            if (this.$router) {
                this.$router.push({ name: "about" });
            }
        },
        detachWebBatteryListeners() {
            if (!this.webBattery) {
                return;
            }
            try {
                this.webBattery.removeEventListener("levelchange", this.onWebBatteryChange);
                this.webBattery.removeEventListener("chargingchange", this.onWebBatteryChange);
            } catch {
                // ignore
            }
            this.webBattery = null;
        },
        onWebBatteryChange() {
            this.refresh();
        },
        async attachWebBatteryListeners() {
            if (this.webBattery) {
                return;
            }
            if (typeof navigator === "undefined" || typeof navigator.getBattery !== "function") {
                return;
            }
            try {
                const battery = await navigator.getBattery();
                if (!battery) {
                    return;
                }
                this.webBattery = battery;
                battery.addEventListener("levelchange", this.onWebBatteryChange);
                battery.addEventListener("chargingchange", this.onWebBatteryChange);
            } catch {
                // Browser may deny Battery Status API.
            }
        },
        async refresh() {
            try {
                this.status = await getDeviceBatteryStatus();
                if (this.status?.source === "web") {
                    await this.attachWebBatteryListeners();
                }
            } catch {
                this.status = null;
            }
        },
    },
};
</script>
