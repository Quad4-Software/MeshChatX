<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-if="isElectron" v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Desktop</div>
                <h2>App Behaviour</h2>
                <p>Control how MeshChat behaves on your desktop.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle opacity-50 cursor-not-allowed">
                <Toggle id="desktop-open-calls-in-separate-window" :model-value="false" :disabled="true" />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.desktop_open_calls_in_separate_window") }}</span>
                    <span class="setting-toggle__description">
                        {{ $t("app.desktop_open_calls_in_separate_window_description") }}
                        <span class="text-blue-500 font-bold block mt-1">(Phased out for now)</span>
                    </span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="desktop-hardware-acceleration-enabled"
                    :model-value="config.desktop_hardware_acceleration_enabled"
                    @update:model-value="$emit('hardware-acceleration-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.desktop_hardware_acceleration_enabled") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("app.desktop_hardware_acceleration_enabled_description")
                    }}</span>
                    <span class="setting-toggle__hint">{{ $t("app.requires_restart") }}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="desktop-tray-enabled"
                    :model-value="desktopCloseSettings.trayEnabled"
                    @update:model-value="$emit('tray-enabled-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.desktop_tray_enabled") }}</span>
                    <span class="setting-toggle__description">{{ $t("app.desktop_tray_enabled_description") }}</span>
                </span>
            </label>

            <label class="flex flex-col gap-2">
                <span class="text-sm font-medium text-sem-fg">{{ $t("app.desktop_close_behavior") }}</span>
                <span class="text-xs text-sem-fg-muted">{{ $t("app.desktop_close_behavior_description") }}</span>
                <select
                    id="desktop-close-behavior"
                    :value="desktopCloseSettings.closeBehavior"
                    class="input-field"
                    @change="$emit('close-behavior-change', $event.target.value)"
                >
                    <option value="ask">{{ $t("app.desktop_close_behavior_ask") }}</option>
                    <option value="quit">{{ $t("app.desktop_close_behavior_quit") }}</option>
                    <option value="background">
                        {{
                            desktopCloseSettings.trayEnabled
                                ? $t("app.desktop_close_behavior_background")
                                : $t("app.desktop_close_behavior_background_no_tray")
                        }}
                    </option>
                </select>
            </label>
        </div>
    </section>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";
import ElectronUtils from "../../../js/ElectronUtils";

export default {
    name: "DesktopSettingsSection",
    components: {
        Toggle,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        config: {
            type: Object,
            required: true,
        },
        desktopCloseSettings: {
            type: Object,
            required: true,
        },
    },
    emits: ["hardware-acceleration-change", "tray-enabled-change", "close-behavior-change"],
    computed: {
        isElectron() {
            return ElectronUtils.isElectron();
        },
    },
};
</script>
