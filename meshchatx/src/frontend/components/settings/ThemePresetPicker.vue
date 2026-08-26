<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3" data-testid="theme-preset-picker">
        <div
            class="relative flex items-center gap-3 rounded-2xl border border-sem-border bg-sem-surface-muted px-3 py-2 focus-within:ring-2 focus-within:ring-sem-focus focus-within:border-sem-focus-border"
        >
            <ThemePresetSwatch :colors="selectedPreviewColors" size="md" />
            <select
                :value="normalizedValue"
                class="min-w-0 flex-1 appearance-none border-0 bg-transparent py-1.5 pr-8 text-sm text-sem-fg focus:outline-hidden focus:ring-0"
                @change="onSelectChange"
            >
                <option v-for="preset in catalog" :key="preset.id" :value="preset.id">
                    {{ $t(preset.labelKey) }}
                </option>
            </select>
            <MaterialDesignIcon
                icon-name="chevron-down"
                class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
                aria-hidden="true"
            />
        </div>

        <div
            class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
            role="listbox"
            :aria-label="$t('app.theme_preset')"
        >
            <button
                v-for="preset in catalog"
                :key="preset.id"
                type="button"
                role="option"
                class="flex min-w-0 items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors hover:bg-sem-surface-muted"
                :class="
                    preset.id === normalizedValue
                        ? 'border-sem-accent bg-sem-surface-muted ring-1 ring-sem-accent/40'
                        : 'border-sem-border'
                "
                :aria-selected="preset.id === normalizedValue ? 'true' : 'false'"
                @click="selectPreset(preset.id)"
            >
                <ThemePresetSwatch :colors="previewColorsForPreset(preset.id)" size="md" />
                <span class="min-w-0 flex-1 truncate text-xs font-medium leading-tight text-sem-fg">
                    {{ $t(preset.labelKey) }}
                </span>
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ThemePresetSwatch from "./ThemePresetSwatch.vue";
import {
    THEME_PRESET_CATALOG,
    getThemePresetPreviewColors,
    normalizeThemePreset,
    normalizeThemePreference,
    resolveEffectiveTheme,
    systemPrefersDark,
} from "../../theme/themeEngine.js";

export default {
    name: "ThemePresetPicker",
    components: {
        MaterialDesignIcon,
        ThemePresetSwatch,
    },
    props: {
        value: {
            type: String,
            default: "default",
        },
        config: {
            type: Object,
            required: true,
        },
    },
    emits: ["update:value", "change"],
    data() {
        return {
            catalog: THEME_PRESET_CATALOG,
        };
    },
    computed: {
        normalizedValue() {
            return normalizeThemePreset(this.value);
        },
        previewMode() {
            return resolveEffectiveTheme(this.config?.theme, systemPrefersDark());
        },
        selectedPreviewColors() {
            return this.previewColorsForPreset(this.normalizedValue);
        },
    },
    methods: {
        previewConfigForPreset(presetId) {
            const next = {
                ...this.config,
                theme: normalizeThemePreference(this.config?.theme),
                theme_preset: presetId,
                accent_color: null,
            };
            if (presetId !== "custom") {
                next.custom_canvas_color = null;
                next.custom_surface_color = null;
            }
            return next;
        },
        previewColorsForPreset(presetId) {
            return getThemePresetPreviewColors(this.previewConfigForPreset(presetId), this.previewMode);
        },
        onSelectChange(event) {
            this.selectPreset(event.target.value);
        },
        selectPreset(presetId) {
            const next = normalizeThemePreset(presetId);
            if (next === this.normalizedValue) {
                return;
            }
            this.$emit("update:value", next);
            this.$emit("change", next);
        },
    },
};
</script>
