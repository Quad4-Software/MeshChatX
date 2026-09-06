<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy } from "svelte";
    import { fade, fly } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        startReactionPickerDrag,
        styleForReactionPickerDragPos,
        type ReactionPickerPoint,
    } from "../lib/reactionPickerDrag.js";

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

    let panelEl: HTMLDivElement | null = $state(null);
    let dragPos: ReactionPickerPoint | null = $state(null);
    let dragCleanup: (() => void) | null = null;

    function isReducedMotion(): boolean {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            return false;
        }
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    const transitionDuration = $derived(isReducedMotion() ? 0 : 120);
    const panelStyle = $derived(dragPos ? styleForReactionPickerDragPos(dragPos) : style);

    function stopDragListeners() {
        if (dragCleanup) {
            dragCleanup();
            dragCleanup = null;
        }
    }

    $effect(() => {
        if (!open) {
            return;
        }
        return () => {
            stopDragListeners();
            dragPos = null;
        };
    });

    onDestroy(() => {
        stopDragListeners();
    });

    function onHeaderPointerDown(event: MouseEvent | TouchEvent) {
        event.preventDefault();
        ondragstart?.(event);
        stopDragListeners();
        dragCleanup = startReactionPickerDrag({
            event,
            getPanel: () => panelEl,
            setPosition: (pos) => {
                dragPos = pos;
            },
        });
    }
</script>

{#if open}
    <div
        class="fixed inset-0 z-40"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onclose?.();
        }}
        role="presentation"
        transition:fade={{ duration: transitionDuration }}
    >
        <div
            bind:this={panelEl}
            class="absolute w-[min(24rem,calc(100%-1rem))] rounded-2xl overflow-hidden border border-sem-border shadow-2xl bg-sem-surface"
            style={panelStyle}
            transition:fly={{ y: 6, duration: transitionDuration }}
        >
            <div
                class="flex items-center justify-between px-3 py-2 border-b border-sem-border cursor-grab active:cursor-grabbing select-none"
                onmousedown={onHeaderPointerDown}
                ontouchstart={onHeaderPointerDown}
                role="presentation"
            >
                <span class="text-xs font-medium text-sem-fg-muted">{t("messages.react")}</span>
                <button
                    type="button"
                    class="p-0.5 rounded-sm hover:bg-sem-surface-muted text-sem-fg-muted focus-ring-sem"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-4" />
                </button>
            </div>
            <emoji-picker
                data-source={emojiPickerDataUrl || undefined}
                class="reaction-emoji-picker {emojiPickerThemeClass}"
                onemoji-click={(e: CustomEvent) => onemojiclick?.(e)}
            ></emoji-picker>
        </div>
    </div>
{/if}

<style>
    :global(.reaction-emoji-picker) {
        width: 100%;
        height: min(280px, 45dvh);
        min-height: 200px;
        --border-radius: 0;
        --border-size: 0;
    }
</style>
