<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ThemePresetPicker from "./ThemePresetPicker.svelte";
    import { normalizeThemePreset } from "../../../theme/themeEngine.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        config: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onthemechange?: () => void;
        onthemepresetchange?: (presetId?: string) => void;
        onaccentcolorchange?: () => void;
        oncustomcanvascolorchange?: () => void;
        oncustomsurfacecolorchange?: () => void;
    }

    let {
        config,
        onupdatefield,
        onthemechange,
        onthemepresetchange,
        onaccentcolorchange,
        oncustomcanvascolorchange,
        oncustomsurfacecolorchange,
    }: Props = $props();

    const themePresetValue = $derived(normalizeThemePreset(config?.theme_preset));
    const accentColorInput = $derived(config?.accent_color || "#2563eb");
    const customCanvasInput = $derived(config?.custom_canvas_color || "#f8fafc");
    const customSurfaceInput = $derived(config?.custom_surface_color || "#ffffff");

    function emitField(key: string, value: any, callback?: () => void) {
        onupdatefield?.({ key, value });
        callback?.();
    }
</script>

<div class="space-y-4">
    <div class="space-y-2">
        <label for="theme-select" class="text-sm font-medium text-sem-fg block">{t("app.theme")}</label>
        <select
            id="theme-select"
            value={config.theme}
            class="input-field"
            onchange={(e) => emitField("theme", (e.target as HTMLSelectElement).value, onthemechange)}
        >
            <option value="light">{t("app.light_theme")}</option>
            <option value="dark">{t("app.dark_theme")}</option>
            <option value="system">{t("app.system_theme")}</option>
        </select>
    </div>

    <div class="space-y-2">
        <div class="text-sm font-medium text-sem-fg">{t("app.theme_preset")}</div>
        <ThemePresetPicker
            value={themePresetValue}
            {config}
            onchange={(presetId) => emitField("theme_preset", presetId, () => onthemepresetchange?.(presetId))}
        />
        <p class="text-xs text-sem-fg-muted">{t("app.theme_preset_description")}</p>
    </div>

    <div class="space-y-2">
        <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium text-sem-fg">{t("app.accent_color")}</div>
            {#if config.accent_color}
                <button
                    type="button"
                    class="text-[10px] font-bold uppercase text-sem-accent hover:underline cursor-pointer"
                    onclick={() => emitField("accent_color", null, onaccentcolorchange)}
                >
                    {t("app.accent_color_reset")}
                </button>
            {/if}
        </div>
        <div class="flex gap-2">
            <input
                value={accentColorInput}
                type="color"
                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                oninput={(e) =>
                    emitField("accent_color", (e.target as HTMLInputElement).value || null, onaccentcolorchange)}
            />
            <input
                value={config.accent_color || ""}
                type="text"
                class="input-field monospace-field flex-1"
                placeholder={t("app.accent_color_placeholder")}
                oninput={(e) =>
                    emitField("accent_color", (e.target as HTMLInputElement).value || null, onaccentcolorchange)}
            />
        </div>
        <p class="text-xs text-sem-fg-muted">{t("app.accent_color_description")}</p>
    </div>

    {#if themePresetValue === "custom"}
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">{t("app.custom_canvas_color")}</div>
                <div class="flex gap-2">
                    <input
                        value={customCanvasInput}
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        oninput={(e) =>
                            emitField(
                                "custom_canvas_color",
                                (e.target as HTMLInputElement).value || null,
                                oncustomcanvascolorchange
                            )}
                    />
                    <input
                        value={config.custom_canvas_color || ""}
                        type="text"
                        class="input-field monospace-field flex-1"
                        oninput={(e) =>
                            emitField(
                                "custom_canvas_color",
                                (e.target as HTMLInputElement).value || null,
                                oncustomcanvascolorchange
                            )}
                    />
                </div>
            </div>
            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">{t("app.custom_surface_color")}</div>
                <div class="flex gap-2">
                    <input
                        value={customSurfaceInput}
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        oninput={(e) =>
                            emitField(
                                "custom_surface_color",
                                (e.target as HTMLInputElement).value || null,
                                oncustomsurfacecolorchange
                            )}
                    />
                    <input
                        value={config.custom_surface_color || ""}
                        type="text"
                        class="input-field monospace-field flex-1"
                        oninput={(e) =>
                            emitField(
                                "custom_surface_color",
                                (e.target as HTMLInputElement).value || null,
                                oncustomsurfacecolorchange
                            )}
                    />
                </div>
            </div>
            <p class="text-xs text-sem-fg-muted sm:col-span-2">{t("app.custom_colors_description")}</p>
        </div>
    {/if}
</div>
