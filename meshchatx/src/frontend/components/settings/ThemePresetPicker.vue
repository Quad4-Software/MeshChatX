<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3" data-testid="theme-preset-picker">
        <div class="flex items-center gap-2 text-sm text-sem-fg-muted">
            <ThemePresetSwatch :colors="selectedPreviewColors" size="md" />
            <span class="font-medium text-sem-fg">{{ $t(selectedPresetLabelKey) }}</span>
        </div>

        <div
            class="flex flex-wrap gap-2.5 py-1"
            role="listbox"
            :aria-label="$t('app.theme_preset')"
            @mouseleave="clearPreview"
        >
            <button
                v-for="preset in catalog"
                :key="preset.id"
                type="button"
                role="option"
                class="theme-preset-dot group relative inline-flex items-center justify-center rounded-full transition-transform duration-150 ease-out hover:z-20 hover:scale-110 focus-visible:z-20 focus-visible:scale-110"
                :class="
                    preset.id === normalizedValue
                        ? 'ring-2 ring-sem-accent ring-offset-2 ring-offset-sem-canvas z-10'
                        : 'ring-1 ring-sem-border/80 hover:ring-sem-accent/50'
                "
                :title="$t(preset.labelKey)"
                :aria-selected="preset.id === normalizedValue ? 'true' : 'false'"
                @click="selectPreset(preset.id)"
                @mouseenter="previewPreset(preset.id)"
                @focus="previewPreset(preset.id)"
                @blur="clearPreview"
            >
                <ThemePresetSwatch :colors="previewColorsForPreset(preset.id)" size="lg" round />
                <span
                    class="pointer-events-none absolute -bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-sem-surface-raised px-2 py-0.5 text-[10px] font-medium text-sem-fg opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100 z-10"
                >
                    {{ $t(preset.labelKey) }}
                </span>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import ThemePresetSwatch from "./ThemePresetSwatch.vue";
import {
    THEME_PRESET_CATALOG,
    applyAppearanceTheme,
    getThemePresetPreviewColors,
    normalizeThemePreset,
    normalizeThemePreference,
    resolveEffectiveTheme,
    systemPrefersDark,
} from "../../theme/themeEngine.js";

const props = withDefaults(
    defineProps<{
        value?: string;
        config: Record<string, any>;
    }>(),
    {
        value: "default",
    }
);

const emit = defineEmits<{
    "update:value": [value: string];
    change: [value: string];
}>();

const catalog = THEME_PRESET_CATALOG;

let previewActive = false;

const normalizedValue = computed(() => normalizeThemePreset(props.value));

const previewMode = computed(() => resolveEffectiveTheme(props.config?.theme, systemPrefersDark()));

const selectedPreviewColors = computed(() => previewColorsForPreset(normalizedValue.value));

const selectedPresetLabelKey = computed(() => {
    const found = (catalog as any[]).find((p) => p.id === normalizedValue.value);
    return found ? found.labelKey : "app.theme_preset_default";
});

function previewConfigForPreset(presetId: string) {
    const next: Record<string, any> = {
        ...props.config,
        theme: normalizeThemePreference(props.config?.theme),
        theme_preset: presetId,
        accent_color: null,
    };
    if (presetId !== "custom") {
        next.custom_canvas_color = null;
        next.custom_surface_color = null;
    }
    return next;
}

function previewColorsForPreset(presetId: string) {
    return getThemePresetPreviewColors(previewConfigForPreset(presetId), previewMode.value);
}

function previewPreset(presetId: string) {
    if (normalizeThemePreset(presetId) === normalizedValue.value) {
        return;
    }
    previewActive = true;
    applyAppearanceTheme(previewConfigForPreset(presetId));
}

function clearPreview() {
    if (!previewActive) {
        return;
    }
    previewActive = false;
    applyAppearanceTheme(props.config);
}

function selectPreset(presetId: string) {
    const next = normalizeThemePreset(presetId);
    if (next === normalizedValue.value) {
        return;
    }
    previewActive = false;
    emit("update:value", next);
    emit("change", next);
}
</script>
