<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="visible" class="space-y-2">
        <div
            v-for="warning in warnings"
            :key="warning.id"
            class="flex items-start gap-3 rounded-xl border border-sem-warning/40 bg-sem-warning/10 px-4 py-3"
        >
            <MaterialDesignIcon :icon-name="warning.icon" class="size-5 mt-0.5 shrink-0 text-sem-warning" />
            <div class="flex-1 min-w-0 space-y-1">
                <div class="text-sm font-semibold text-sem-warning">
                    {{ $t(warning.titleKey) }}
                </div>
                <ul class="text-xs text-sem-warning list-disc pl-4 space-y-0.5">
                    <li v-for="key in warning.suggestionKeys" :key="key">{{ $t(key) }}</li>
                </ul>
                <div v-if="warning.actions?.length" class="pt-1 flex flex-wrap gap-2">
                    <button
                        v-for="action in warning.actions"
                        :key="action.id"
                        class="inline-flex items-center gap-1.5 rounded-lg border border-sem-warning/40 bg-sem-warning/10 px-2.5 py-1 text-xs font-bold text-sem-warning hover:bg-sem-warning/20 transition-colors"
                        @click="emit('action', action.id)"
                    >
                        <MaterialDesignIcon :icon-name="action.icon" class="size-3.5" />
                        <span>{{ $t(action.labelKey) }}</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { transportSuggestionKeys, TRANSPORT_SERIAL, TRANSPORT_BLUETOOTH } from "../../js/rnode/Capabilities.js";

const props = withDefaults(
    defineProps<{
        capabilities: Record<string, any>;
        androidAvailable?: boolean;
    }>(),
    {
        androidAvailable: false,
    }
);

const emit = defineEmits<{
    action: [action: any];
}>();

function serialActions(serial: any): any[] {
    const actions: any[] = [];
    if (serial?.reason === "polyfill_not_loaded") {
        actions.push({
            id: "load-polyfill",
            icon: "download",
            labelKey: "tools.rnode_flasher.support.actions.load_polyfill",
        });
    }
    if (props.androidAvailable) {
        actions.push({
            id: "open-native-flasher",
            icon: "usb",
            labelKey: "tools.rnode_flasher.support.actions.open_native",
        });
    }
    return actions;
}

function bluetoothActions(): any[] {
    const actions: any[] = [];
    const bluetooth = props.capabilities?.transports?.[TRANSPORT_BLUETOOTH];
    if (props.androidAvailable) {
        const needsPermission = bluetooth?.reason === "android_bluetooth_permission_required";
        if (needsPermission) {
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
        } else {
            // Permissions granted (or N/A). WebView still cannot flash over BLE.
            actions.push({
                id: "open-native-flasher",
                icon: "usb",
                labelKey: "tools.rnode_flasher.support.actions.open_native",
            });
            actions.push({
                id: "open-bluetooth-settings",
                icon: "cog",
                labelKey: "tools.rnode_flasher.support.actions.open_settings",
            });
        }
        return actions;
    }
    // Desktop browsers: Web Bluetooth has no ambient permission grant.
    // The chooser from requestDevice() is the permission UI. Offer a probe
    // that either opens it or tells the user how to enable the API (Brave).
    actions.push({
        id: "probe-bluetooth",
        icon: "bluetooth-connect",
        labelKey: "tools.rnode_flasher.support.actions.probe_bluetooth",
    });
    actions.push({
        id: "recheck-capabilities",
        icon: "refresh",
        labelKey: "tools.rnode_flasher.support.actions.recheck_capabilities",
    });
    return actions;
}

const warnings = computed(() => {
    const warnings: any[] = [];
    const serial = props.capabilities?.transports?.[TRANSPORT_SERIAL];
    const bluetooth = props.capabilities?.transports?.[TRANSPORT_BLUETOOTH];

    if (serial && !serial.available) {
        warnings.push({
            id: "serial",
            icon: "usb-port",
            titleKey: "tools.rnode_flasher.support.serial.title",
            suggestionKeys: transportSuggestionKeys(props.capabilities, TRANSPORT_SERIAL),
            actions: serialActions(serial),
        });
    }
    if (bluetooth && !bluetooth.available) {
        warnings.push({
            id: "bluetooth",
            icon: "bluetooth",
            titleKey: "tools.rnode_flasher.support.bluetooth.title",
            suggestionKeys: transportSuggestionKeys(props.capabilities, TRANSPORT_BLUETOOTH),
            actions: bluetoothActions(),
        });
    }
    return warnings;
});

const visible = computed(() => warnings.value.length > 0);
</script>
