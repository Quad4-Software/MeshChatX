<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{{ $t("settings.bandwidth.eyebrow") }}</div>
                <h2>{{ $t("settings.bandwidth.title") }}</h2>
                <p>{{ $t("settings.bandwidth.description") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <SettingToggleRow
                id="settings-limited-bandwidth-enabled"
                :model-value="config.limited_bandwidth_enabled === true"
                :title="$t('settings.bandwidth.enabled')"
                :description="$t('settings.bandwidth.enabled_desc')"
                @update:model-value="emit('enabled-change', $event)"
            />
            <div
                v-if="config.limited_bandwidth_enabled === true"
                class="rounded-xl border border-sem-border bg-sem-surface-muted px-3 py-2 text-xs text-sem-fg-muted"
                aria-live="polite"
            >
                <span class="font-semibold text-sem-fg">{{ $t("settings.bandwidth.active_badge") }}</span>
                {{ $t("settings.bandwidth.active_summary") }}
            </div>
        </div>
    </section>
</template>

<script setup lang="ts">
import SettingToggleRow from "../SettingToggleRow.vue";

withDefaults(
    defineProps<{
        visible?: boolean;
        config: Record<string, any>;
    }>(),
    {
        visible: true,
    }
);

const emit = defineEmits<{
    "enabled-change": [enabled: boolean];
}>();
</script>
