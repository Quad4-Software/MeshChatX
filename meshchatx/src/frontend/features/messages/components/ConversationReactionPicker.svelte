<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        open = false,
        style = "",
        emojiPickerDataUrl = "",
        emojiPickerThemeClass = "",
        onclose,
        onemojiclick,
        ondragstart,
    }: {
        open?: boolean;
        style?: string;
        emojiPickerDataUrl?: string;
        emojiPickerThemeClass?: string;
        onclose?: () => void;
        onemojiclick?: (event: CustomEvent) => void;
        ondragstart?: (event: MouseEvent | TouchEvent) => void;
    } = $props();
</script>

{#if open}
    <div
        class="absolute inset-0 z-40"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onclose?.();
        }}
        role="presentation"
    >
        <div
            class="absolute w-[min(24rem,calc(100%-1rem))] rounded-2xl overflow-hidden border border-sem-border shadow-2xl bg-sem-surface"
            {style}
        >
            <div
                class="flex items-center justify-between px-3 py-2 border-b border-sem-border cursor-grab active:cursor-grabbing select-none"
                onmousedown={(e) => {
                    e.preventDefault();
                    ondragstart?.(e);
                }}
                ontouchstart={(e) => {
                    e.preventDefault();
                    ondragstart?.(e);
                }}
                role="presentation"
            >
                <span class="text-xs font-medium text-sem-fg-muted">{t("messages.react")}</span>
                <button
                    type="button"
                    class="p-0.5 rounded-sm hover:bg-sem-surface-muted text-sem-fg-muted"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-4" />
                </button>
            </div>
            <!-- emoji-picker is a custom element from emoji-picker-element -->
            <emoji-picker
                data-source={emojiPickerDataUrl}
                class="reaction-emoji-picker {emojiPickerThemeClass}"
                onemoji-click={(e: CustomEvent) => onemojiclick?.(e)}
            ></emoji-picker>
        </div>
    </div>
{/if}
