<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import {
        buildThemeVariableOverrides,
        resolveEffectiveTheme,
        systemPrefersDark,
    } from "../../../theme/themeEngine.js";
    import {
        MESHCHAT_THEME_VARIABLES_DARK,
        MESHCHAT_THEME_VARIABLES_LIGHT,
    } from "../../../theme/designTokens.js";

    interface Props {
        config: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onbubblecolorchange?: (type: string) => void;
    }

    type BubbleColorType = "outbound" | "failed" | "waiting";

    let { config, onupdatefield, onbubblecolorchange }: Props = $props();

    const resolvedBubbleColors = $derived.by((): Record<BubbleColorType, string | undefined> => {
        const mode = resolveEffectiveTheme(config?.theme, systemPrefersDark());
        const base = mode === "dark" ? MESHCHAT_THEME_VARIABLES_DARK : MESHCHAT_THEME_VARIABLES_LIGHT;
        const resolved = { ...base, ...buildThemeVariableOverrides(config, mode) };
        return {
            outbound: resolved["--mc-bubble-outbound"],
            failed: resolved["--mc-bubble-failed"],
            waiting: resolved["--mc-bubble-waiting"],
        };
    });

    function emitBubble(key: string, value: string | null, type: string) {
        onupdatefield?.({ key, value });
        onbubblecolorchange?.(type);
    }

    function onBubbleColorInput(type: string, event: Event) {
        emitBubble(`message_${type}_bubble_color`, (event.target as HTMLInputElement).value, type);
    }

    function isThemeBubbleColor(type: string): boolean {
        const raw = config?.[`message_${type}_bubble_color`];
        const hex = String(raw ?? "")
            .trim()
            .toLowerCase();
        if (hex === "") {
            return true;
        }
        if (type === "outbound") {
            return hex === "#4f46e5";
        }
        if (type === "failed") {
            return hex === "#ef4444" || hex === "#dc2626";
        }
        if (type === "waiting") {
            return hex === "#e5e7eb" || hex === "#3f3f46";
        }
        return false;
    }

    function bubbleColorInputValue(type: BubbleColorType): string {
        if (isThemeBubbleColor(type)) {
            return resolvedBubbleColors[type] || "#000000";
        }
        return String(config?.[`message_${type}_bubble_color`] ?? "").trim();
    }

    function onInboundBubbleReset() {
        emitBubble("message_inbound_bubble_color", null, "inbound");
    }

    function onInboundBubbleCustomize() {
        emitBubble("message_inbound_bubble_color", "#ffffff", "inbound");
    }
</script>

<div class="space-y-4">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {#each ["outbound", "failed", "waiting"] as type (type)}
            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {t(`settings.${type}_bubble_color`)}
                </div>
                <div class="flex gap-2">
                    <input
                        value={bubbleColorInputValue(type as BubbleColorType)}
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        data-testid={`bubble-color-${type}`}
                        oninput={(e) => onBubbleColorInput(type, e)}
                    />
                    <input
                        value={bubbleColorInputValue(type as BubbleColorType)}
                        type="text"
                        class="input-field monospace-field flex-1"
                        data-testid={`bubble-color-${type}-text`}
                        oninput={(e) => onBubbleColorInput(type, e)}
                    />
                </div>
                {#if isThemeBubbleColor(type)}
                    <p class="text-[11px] text-sem-fg-muted">
                        {t("settings.inbound_bubble_default_hint")}
                    </p>
                {/if}
            </div>
        {/each}
    </div>

    <div class="space-y-2">
        <div class="flex items-center justify-between">
            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                {t("settings.inbound_bubble_color")}
            </div>
            {#if config.message_inbound_bubble_color}
                <button
                    type="button"
                    class="text-[10px] text-red-500 font-bold uppercase hover:underline cursor-pointer"
                    onclick={onInboundBubbleReset}
                >
                    {t("settings.inbound_bubble_reset")}
                </button>
            {/if}
        </div>
        <div class="flex gap-2">
            {#if config.message_inbound_bubble_color}
                <input
                    value={config.message_inbound_bubble_color}
                    type="color"
                    class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                    oninput={(e) => onBubbleColorInput("inbound", e)}
                />
            {/if}
            {#if !config.message_inbound_bubble_color}
                <div
                    class="flex-1 flex items-center px-3 text-xs text-gray-400 bg-sem-surface-muted rounded-xl border border-dashed border-sem-border italic"
                >
                    {t("settings.inbound_bubble_default_hint")}
                    <button
                        type="button"
                        class="ml-2 px-2 py-1 bg-blue-500 text-white rounded-lg not-italic font-bold cursor-pointer"
                        onclick={onInboundBubbleCustomize}
                    >
                        {t("settings.inbound_bubble_customize")}
                    </button>
                </div>
            {:else}
                <input
                    value={config.message_inbound_bubble_color}
                    type="text"
                    class="input-field monospace-field flex-1"
                    oninput={(e) => onBubbleColorInput("inbound", e)}
                />
            {/if}
        </div>
    </div>
</div>
