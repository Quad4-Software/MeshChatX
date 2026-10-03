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
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("visualiser.renderer_title") }}
                </div>
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("visualiser.renderer_desc") }}
                </p>
                <SegmentedControl
                    id="settings-visualiser-renderer"
                    :model-value="renderer"
                    :options="rendererOptions"
                    @change="$emit('renderer-change', $event)"
                />
            </div>
            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("visualiser.view_mode") }}
                </div>
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("visualiser.view_mode_desc") }}
                </p>
                <SegmentedControl
                    id="settings-visualiser-view-mode"
                    :model-value="viewMode"
                    :options="viewModeOptions"
                    @change="$emit('view-mode-change', $event)"
                />
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
import SegmentedControl from "../../forms/SegmentedControl.vue";

export default {
    name: "VisualiserSettingsSection",
    components: {
        SegmentedControl,
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
    computed: {
        rendererOptions() {
            return [
                { value: "auto", label: "visualiser.renderer_option_auto" },
                { value: "webgl", label: "visualiser.renderer_option_webgl" },
                { value: "vis", label: "visualiser.renderer_option_vis" },
            ];
        },
        viewModeOptions() {
            return [
                { value: "flat", icon: "earth", label: "visualiser.view_mode_flat_full" },
                { value: "planet", icon: "orbit", label: "visualiser.view_mode_planet_full" },
            ];
        },
    },
};
</script>
