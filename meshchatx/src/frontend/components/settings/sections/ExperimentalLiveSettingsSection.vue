<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{{ $t("settings.experimental.eyebrow") }}</div>
                <h2>{{ $t("settings.experimental.title") }}</h2>
                <p>{{ $t("settings.experimental.description") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <Toggle
                    id="settings-wt-sidecar-enabled"
                    :model-value="sidecarEnabled"
                    @update:model-value="$emit('sidecar-change', $event)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.experimental.webtransport_sidecar") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.experimental.webtransport_sidecar_desc")
                    }}</span>
                </span>
            </label>

            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("settings.experimental.live_transport_mode") }}
                </div>
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("settings.experimental.live_transport_mode_desc") }}
                </p>
                <SegmentedControl
                    :model-value="liveTransportMode"
                    :options="liveTransportOptions"
                    @change="$emit('mode-change', $event)"
                />
            </div>
        </div>
    </section>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";
import SegmentedControl from "../../forms/SegmentedControl.vue";

export default {
    name: "ExperimentalLiveSettingsSection",
    components: {
        SegmentedControl,
        Toggle,
    },
    props: {
        visible: { type: Boolean, default: false },
        liveTransportMode: { type: String, default: "auto" },
        sidecarEnabled: { type: Boolean, default: false },
    },
    emits: ["mode-change", "sidecar-change"],
    computed: {
        liveTransportOptions() {
            return [
                { value: "auto", icon: "auto-fix", label: "settings.experimental.mode_auto" },
                { value: "websocket", icon: "web", label: "settings.experimental.mode_websocket" },
                {
                    value: "webtransport",
                    icon: "rocket-launch-outline",
                    label: "settings.experimental.mode_webtransport",
                },
            ];
        },
    },
};
</script>
