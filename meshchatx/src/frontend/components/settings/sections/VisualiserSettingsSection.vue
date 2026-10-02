<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Visualiser</div>
                <h2>{{ $t("visualiser.title") }}</h2>
                <p>{{ $t("visualiser.description") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("visualiser.renderer_title") }}
                </div>
                <p class="text-xs text-gray-600 dark:text-gray-400">
                    {{ $t("visualiser.renderer_desc") }}
                </p>
                <select
                    id="settings-visualiser-renderer"
                    :value="renderer"
                    class="input-field"
                    @change="$emit('renderer-change', $event.target.value)"
                >
                    <option value="auto">{{ $t("visualiser.renderer_option_auto") }}</option>
                    <option value="webgl">{{ $t("visualiser.renderer_option_webgl") }}</option>
                    <option value="vis">{{ $t("visualiser.renderer_option_vis") }}</option>
                </select>
            </div>
            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("visualiser.view_mode") }}
                </div>
                <p class="text-xs text-gray-600 dark:text-gray-400">
                    {{ $t("visualiser.view_mode_desc") }}
                </p>
                <select
                    id="settings-visualiser-view-mode"
                    :value="viewMode"
                    class="input-field"
                    @change="$emit('view-mode-change', $event.target.value)"
                >
                    <option value="flat">{{ $t("visualiser.view_mode_flat_full") }}</option>
                    <option value="planet">{{ $t("visualiser.view_mode_planet_full") }}</option>
                </select>
            </div>
            <label class="setting-toggle">
                <Toggle
                    id="settings-visualiser-offline"
                    :model-value="showDisabledInterfaces"
                    @update:model-value="$emit('show-disabled-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("visualiser.show_disabled_interfaces") }}</span>
                </span>
            </label>
            <label class="setting-toggle">
                <Toggle
                    id="settings-visualiser-discovered"
                    :model-value="showDiscoveredInterfaces"
                    @update:model-value="$emit('show-discovered-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("visualiser.show_discovered_interfaces") }}</span>
                </span>
            </label>
        </div>
    </section>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";

export default {
    name: "VisualiserSettingsSection",
    components: {
        Toggle,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        renderer: {
            type: String,
            default: "auto",
        },
        viewMode: {
            type: String,
            default: "flat",
        },
        showDisabledInterfaces: {
            type: Boolean,
            default: false,
        },
        showDiscoveredInterfaces: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["renderer-change", "view-mode-change", "show-disabled-change", "show-discovered-change"],
};
</script>
