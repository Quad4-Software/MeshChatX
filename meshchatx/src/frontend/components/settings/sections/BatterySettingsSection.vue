<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{{ $t("settings.battery.eyebrow") }}</div>
                <h2>{{ $t("settings.battery.title") }}</h2>
                <p>{{ $t("settings.battery.description") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-saver-enabled"
                    :model-value="batterySaver.enabled"
                    @update:model-value="$emit('enabled-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.battery.enabled") }}</span>
                    <span class="setting-toggle__description">{{ $t("settings.battery.enabled_desc") }}</span>
                </span>
            </label>

            <div class="text-sm font-medium text-gray-900 dark:text-gray-100 pt-2">
                {{ $t("settings.battery.options_heading") }}
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-viz-discovery"
                    :model-value="batterySaver.disableVisualiserDiscovery"
                    @update:model-value="$emit('patch', { disableVisualiserDiscovery: $event })"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.battery.disable_visualiser_discovery") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.battery.disable_visualiser_discovery_desc")
                    }}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-hide-offline"
                    :model-value="batterySaver.hideOfflineInterfaces"
                    @update:model-value="$emit('patch', { hideOfflineInterfaces: $event })"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.battery.hide_offline_interfaces") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.battery.hide_offline_interfaces_desc")
                    }}</span>
                </span>
            </label>

            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("settings.battery.max_visualiser_interfaces") }}
                </div>
                <p class="text-xs text-gray-500 dark:text-zinc-400">
                    {{ $t("settings.battery.max_visualiser_interfaces_desc") }}
                </p>
                <input
                    :value="batterySaver.maxVisualiserInterfaces"
                    type="number"
                    min="0"
                    max="128"
                    class="input-field"
                    @change="
                        $emit('patch', {
                            maxVisualiserInterfaces: Number($event.target.value),
                        })
                    "
                />
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("settings.battery.visualiser_reload_seconds") }}
                </div>
                <p class="text-xs text-gray-500 dark:text-zinc-400">
                    {{ $t("settings.battery.visualiser_reload_seconds_desc") }}
                </p>
                <input
                    :value="batterySaver.visualiserReloadSeconds"
                    type="number"
                    min="0"
                    max="600"
                    class="input-field"
                    @change="
                        $emit('patch', {
                            visualiserReloadSeconds: Number($event.target.value),
                        })
                    "
                />
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-live-layout"
                    :model-value="batterySaver.disableVisualiserLiveLayout"
                    @update:model-value="$emit('patch', { disableVisualiserLiveLayout: $event })"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{
                        $t("settings.battery.disable_visualiser_live_layout")
                    }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.battery.disable_visualiser_live_layout_desc")
                    }}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-bg-poll"
                    :model-value="batterySaver.reduceBackgroundPolling"
                    @update:model-value="$emit('patch', { reduceBackgroundPolling: $event })"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.battery.reduce_background_polling") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.battery.reduce_background_polling_desc")
                    }}</span>
                </span>
            </label>

            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("settings.battery.background_poll_multiplier") }}
                </div>
                <p class="text-xs text-gray-500 dark:text-zinc-400">
                    {{ $t("settings.battery.background_poll_multiplier_desc") }}
                </p>
                <input
                    :value="batterySaver.backgroundPollMultiplier"
                    type="number"
                    min="2"
                    max="10"
                    class="input-field"
                    @change="
                        $emit('patch', {
                            backgroundPollMultiplier: Number($event.target.value),
                        })
                    "
                />
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-ifaces-discovery"
                    :model-value="batterySaver.reduceInterfacesDiscovery"
                    @update:model-value="$emit('patch', { reduceInterfacesDiscovery: $event })"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.battery.reduce_interfaces_discovery") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.battery.reduce_interfaces_discovery_desc")
                    }}</span>
                </span>
            </label>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {{ $t("settings.battery.interfaces_stats_poll_seconds") }}
                    </div>
                    <input
                        :value="batterySaver.interfacesStatsPollSeconds"
                        type="number"
                        min="1"
                        max="120"
                        class="input-field"
                        @change="
                            $emit('patch', {
                                interfacesStatsPollSeconds: Number($event.target.value),
                            })
                        "
                    />
                </div>
                <div class="space-y-2">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {{ $t("settings.battery.interfaces_discovery_poll_seconds") }}
                    </div>
                    <input
                        :value="batterySaver.interfacesDiscoveryPollSeconds"
                        type="number"
                        min="5"
                        max="300"
                        class="input-field"
                        @change="
                            $emit('patch', {
                                interfacesDiscoveryPollSeconds: Number($event.target.value),
                            })
                        "
                    />
                </div>
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-bitrate-limits"
                    :model-value="batterySaver.applyInterfaceBitrateLimits"
                    @update:model-value="$emit('patch', { applyInterfaceBitrateLimits: $event === true })"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{
                        $t("settings.battery.apply_interface_bitrate_limits")
                    }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.battery.apply_interface_bitrate_limits_desc")
                    }}</span>
                </span>
            </label>

            <div v-if="batterySaver.applyInterfaceBitrateLimits" class="space-y-3">
                <p class="text-xs text-gray-500 dark:text-zinc-400">
                    {{ $t("settings.battery.interface_bitrate_limits_help") }}
                </p>
                <div v-if="batteryInterfaceRows.length === 0" class="text-xs text-gray-500 dark:text-zinc-400">
                    {{ $t("settings.battery.interface_bitrate_limits_empty") }}
                </div>
                <div
                    v-for="row in batteryInterfaceRows"
                    :key="row.name"
                    class="grid grid-cols-1 sm:grid-cols-[1fr_10rem] gap-2 items-center"
                >
                    <div class="text-sm text-gray-900 dark:text-gray-100 truncate" :title="row.name">
                        {{ row.name }}
                        <span class="text-xs text-gray-500 dark:text-zinc-400"> ({{ row.type || "?" }}) </span>
                    </div>
                    <input
                        :value="batterySaver.interfaceBitrateLimits[row.name]"
                        type="number"
                        min="0"
                        class="input-field"
                        :placeholder="$t('settings.battery.interface_bitrate_placeholder')"
                        @change="onBitrateInput(row.name, $event.target.value)"
                    />
                </div>
                <div class="flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="secondary-button text-sm"
                        :disabled="batteryBitrateBusy"
                        @click="$emit('apply-bitrates')"
                    >
                        {{ $t("settings.battery.apply_bitrates_reload") }}
                    </button>
                    <button
                        type="button"
                        class="secondary-button text-sm"
                        :disabled="batteryBitrateBusy"
                        @click="$emit('restore-bitrates')"
                    >
                        {{ $t("settings.battery.restore_bitrates_reload") }}
                    </button>
                </div>
            </div>
        </div>
    </section>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";

export default {
    name: "BatterySettingsSection",
    components: {
        Toggle,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        batterySaver: {
            type: Object,
            required: true,
        },
        batteryInterfaceRows: {
            type: Array,
            default: () => [],
        },
        batteryBitrateBusy: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["enabled-change", "patch", "bitrate-limit-change", "apply-bitrates", "restore-bitrates"],
    methods: {
        onBitrateInput(name, raw) {
            const limits = { ...(this.batterySaver.interfaceBitrateLimits || {}) };
            if (raw === "" || raw == null || Number.isNaN(Number(raw))) {
                delete limits[name];
            } else {
                limits[name] = Math.max(0, Math.round(Number(raw)));
            }
            this.$emit("patch", { interfaceBitrateLimits: limits });
        },
    },
};
</script>
