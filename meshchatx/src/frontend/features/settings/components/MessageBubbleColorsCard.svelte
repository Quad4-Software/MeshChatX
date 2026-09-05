<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        config: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onbubblecolorchange?: (type: string) => void;
    }

    let { config, onupdatefield, onbubblecolorchange }: Props = $props();

    const outboundBubbleColorInput = $derived(config?.message_outbound_bubble_color || "#4f46e5");
    const inboundBubbleColorInput = $derived(config?.message_inbound_bubble_color || "#f3f4f6");
    const failedBubbleColorInput = $derived(config?.message_failed_bubble_color || "#ef4444");
    const waitingBubbleColorInput = $derived(config?.message_waiting_bubble_color || "#e5e7eb");

    function emitBubble(key: string, value: string | null, type: string) {
        onupdatefield?.({ key, value });
        onbubblecolorchange?.(type);
    }
</script>

<div class="space-y-4">
    <div class="space-y-2">
        <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium text-sem-fg">{t("app.message_outbound_bubble_color")}</div>
            {#if config.message_outbound_bubble_color}
                <button
                    type="button"
                    class="text-[10px] font-bold uppercase text-sem-accent hover:underline cursor-pointer"
                    onclick={() => emitBubble("message_outbound_bubble_color", null, "outbound")}
                >
                    {t("app.accent_color_reset")}
                </button>
            {/if}
        </div>
        <div class="flex gap-2">
            <input
                value={outboundBubbleColorInput}
                type="color"
                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                oninput={(e) =>
                    emitBubble(
                        "message_outbound_bubble_color",
                        (e.target as HTMLInputElement).value || null,
                        "outbound"
                    )}
            />
            <input
                value={config.message_outbound_bubble_color || ""}
                type="text"
                class="input-field monospace-field flex-1"
                placeholder="#4f46e5"
                oninput={(e) =>
                    emitBubble(
                        "message_outbound_bubble_color",
                        (e.target as HTMLInputElement).value || null,
                        "outbound"
                    )}
            />
        </div>
    </div>

    <div class="space-y-2">
        <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium text-sem-fg">{t("app.message_inbound_bubble_color")}</div>
            {#if config.message_inbound_bubble_color}
                <button
                    type="button"
                    class="text-[10px] font-bold uppercase text-sem-accent hover:underline cursor-pointer"
                    onclick={() => emitBubble("message_inbound_bubble_color", null, "inbound")}
                >
                    {t("app.accent_color_reset")}
                </button>
            {/if}
        </div>
        <div class="flex gap-2">
            <input
                value={inboundBubbleColorInput}
                type="color"
                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                oninput={(e) =>
                    emitBubble("message_inbound_bubble_color", (e.target as HTMLInputElement).value || null, "inbound")}
            />
            <input
                value={config.message_inbound_bubble_color || ""}
                type="text"
                class="input-field monospace-field flex-1"
                placeholder={t("app.message_inbound_bubble_color_placeholder")}
                oninput={(e) =>
                    emitBubble("message_inbound_bubble_color", (e.target as HTMLInputElement).value || null, "inbound")}
            />
        </div>
    </div>

    <div class="space-y-2">
        <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium text-sem-fg">{t("app.message_failed_bubble_color")}</div>
            {#if config.message_failed_bubble_color}
                <button
                    type="button"
                    class="text-[10px] font-bold uppercase text-sem-accent hover:underline cursor-pointer"
                    onclick={() => emitBubble("message_failed_bubble_color", null, "failed")}
                >
                    {t("app.accent_color_reset")}
                </button>
            {/if}
        </div>
        <div class="flex gap-2">
            <input
                value={failedBubbleColorInput}
                type="color"
                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                oninput={(e) =>
                    emitBubble("message_failed_bubble_color", (e.target as HTMLInputElement).value || null, "failed")}
            />
            <input
                value={config.message_failed_bubble_color || ""}
                type="text"
                class="input-field monospace-field flex-1"
                placeholder="#ef4444"
                oninput={(e) =>
                    emitBubble("message_failed_bubble_color", (e.target as HTMLInputElement).value || null, "failed")}
            />
        </div>
    </div>

    <div class="space-y-2">
        <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium text-sem-fg">{t("app.message_waiting_bubble_color")}</div>
            {#if config.message_waiting_bubble_color}
                <button
                    type="button"
                    class="text-[10px] font-bold uppercase text-sem-accent hover:underline cursor-pointer"
                    onclick={() => emitBubble("message_waiting_bubble_color", null, "waiting")}
                >
                    {t("app.accent_color_reset")}
                </button>
            {/if}
        </div>
        <div class="flex gap-2">
            <input
                value={waitingBubbleColorInput}
                type="color"
                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                oninput={(e) =>
                    emitBubble("message_waiting_bubble_color", (e.target as HTMLInputElement).value || null, "waiting")}
            />
            <input
                value={config.message_waiting_bubble_color || ""}
                type="text"
                class="input-field monospace-field flex-1"
                placeholder="#e5e7eb"
                oninput={(e) =>
                    emitBubble("message_waiting_bubble_color", (e.target as HTMLInputElement).value || null, "waiting")}
            />
        </div>
    </div>
</div>
