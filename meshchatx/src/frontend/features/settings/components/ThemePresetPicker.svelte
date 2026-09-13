<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ThemePresetSwatch from "./ThemePresetSwatch.svelte";
    import {
        THEME_PRESET_CATALOG,
        getThemePresetPreviewColors,
        normalizeThemePreset,
        normalizeThemePreference,
        resolveEffectiveTheme,
        systemPrefersDark,
    } from "../../../theme/themeEngine.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        value?: string;
        config: Record<string, any>;
        onchange?: (preset: string) => void;
    }

    let { value = "default", config, onchange }: Props = $props();

    const catalog = THEME_PRESET_CATALOG;
    const normalizedValue = $derived(normalizeThemePreset(value));
    const previewMode = $derived(resolveEffectiveTheme(config?.theme, systemPrefersDark()));

    function previewConfigForPreset(presetId: string): Record<string, unknown> {
        const next: Record<string, unknown> = {
            ...config,
            theme: normalizeThemePreference(config?.theme),
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
        return getThemePresetPreviewColors(previewConfigForPreset(presetId), previewMode);
    }

    const selectedPreviewColors = $derived(previewColorsForPreset(normalizedValue));

    function selectPreset(presetId: string) {
        const next = normalizeThemePreset(presetId);
        if (next === normalizedValue) return;
        onchange?.(next);
    }

    function onSelectChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        selectPreset(target.value);
    }
</script>

<div class="space-y-3" data-testid="theme-preset-picker">
    <div
        class="relative flex items-center gap-3 rounded-2xl border border-sem-border bg-sem-surface-muted px-3 py-2 focus-within:ring-2 focus-within:ring-sem-focus focus-within:border-sem-focus-border"
    >
        <ThemePresetSwatch colors={selectedPreviewColors} size="md" />
        <select
            value={normalizedValue}
            class="min-w-0 flex-1 appearance-none border-0 bg-transparent py-1.5 pr-8 text-sm text-sem-fg focus:outline-hidden focus:ring-0"
            onchange={onSelectChange}
        >
            {#each catalog as preset (preset.id)}
                <option value={preset.id}>
                    {t(preset.labelKey)}
                </option>
            {/each}
        </select>
        <MaterialDesignIcon
            iconName="chevron-down"
            class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
        />
    </div>

    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4" role="listbox" aria-label={t("app.theme_preset")}>
        {#each catalog as preset (preset.id)}
            <button
                type="button"
                role="option"
                class="flex min-w-0 items-center gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors hover:bg-sem-surface-muted {preset.id ===
                normalizedValue
                    ? 'border-sem-accent bg-sem-surface-muted ring-1 ring-sem-accent/40'
                    : 'border-sem-border'}"
                aria-selected={preset.id === normalizedValue ? "true" : "false"}
                onclick={() => selectPreset(preset.id)}
            >
                <ThemePresetSwatch colors={previewColorsForPreset(preset.id)} size="md" />
                <span class="min-w-0 flex-1 truncate text-xs font-medium leading-tight text-sem-fg">
                    {t(preset.labelKey)}
                </span>
            </button>
        {/each}
    </div>
</div>
