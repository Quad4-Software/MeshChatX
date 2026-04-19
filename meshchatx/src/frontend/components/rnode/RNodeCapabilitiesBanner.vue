<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="visible" class="space-y-2">
        <div
            v-for="warning in warnings"
            :key="warning.id"
            class="flex items-start gap-3 rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3"
        >
            <MaterialDesignIcon
                :icon-name="warning.icon"
                class="size-5 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400"
            />
            <div class="flex-1 min-w-0 space-y-1">
                <div class="text-sm font-semibold text-amber-800 dark:text-amber-200">
                    {{ $t(warning.titleKey) }}
                </div>
                <ul class="text-xs text-amber-700 dark:text-amber-300 list-disc pl-4 space-y-0.5">
                    <li v-for="key in warning.suggestionKeys" :key="key">{{ $t(key) }}</li>
                </ul>
                <div v-if="warning.actions?.length" class="pt-1 flex flex-wrap gap-2">
                    <button
                        v-for="action in warning.actions"
                        :key="action.id"
                        class="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-amber-900/30 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-200 hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors"
                        @click="$emit('action', action.id)"
                    >
                        <MaterialDesignIcon :icon-name="action.icon" class="size-3.5" />
                        <span>{{ $t(action.labelKey) }}</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { transportSuggestionKeys, TRANSPORT_SERIAL, TRANSPORT_BLUETOOTH } from "../../js/rnode/Capabilities.js";

export default {
    name: "RNodeCapabilitiesBanner",
    components: { MaterialDesignIcon },
    props: {
        capabilities: {
            type: Object,
            required: true,
        },
        androidAvailable: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["action"],
    computed: {
        warnings() {
            const warnings = [];
            const serial = this.capabilities?.transports?.[TRANSPORT_SERIAL];
            const bluetooth = this.capabilities?.transports?.[TRANSPORT_BLUETOOTH];

            if (serial && !serial.available) {
                warnings.push({
                    id: "serial",
                    icon: "usb-port",
                    titleKey: "tools.rnode_flasher.support.serial.title",
                    suggestionKeys: transportSuggestionKeys(this.capabilities, TRANSPORT_SERIAL),
                    actions: this._serialActions(serial),
                });
            }
            if (bluetooth && !bluetooth.available) {
                warnings.push({
                    id: "bluetooth",
                    icon: "bluetooth",
                    titleKey: "tools.rnode_flasher.support.bluetooth.title",
                    suggestionKeys: transportSuggestionKeys(this.capabilities, TRANSPORT_BLUETOOTH),
                    actions: this._bluetoothActions(),
                });
            }
            return warnings;
        },
        visible() {
            return this.warnings.length > 0;
        },
    },
    methods: {
        _serialActions(serial) {
            const actions = [];
            if (serial?.reason === "polyfill_not_loaded") {
                actions.push({
                    id: "load-polyfill",
                    icon: "download",
                    labelKey: "tools.rnode_flasher.support.actions.load_polyfill",
                });
            }
            return actions;
        },
        _bluetoothActions() {
            const actions = [];
            if (this.androidAvailable) {
                actions.push({
                    id: "request-bluetooth",
                    icon: "bluetooth-settings",
                    labelKey: "tools.rnode_flasher.support.actions.request_bluetooth",
                });
                actions.push({
                    id: "open-bluetooth-settings",
                    icon: "cog",
                    labelKey: "tools.rnode_flasher.support.actions.open_settings",
                });
            }
            return actions;
        },
    },
};
</script>
