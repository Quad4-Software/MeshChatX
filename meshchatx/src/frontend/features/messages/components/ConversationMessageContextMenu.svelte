<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";

    let {
        show = false,
        x = 0,
        y = 0,
        justOpened = false,
        openedFromBubble = false,
        canCopy = false,
        canTranslate = false,
        canReact = true,
        hasImage = false,
        canSaveAsGif = false,
        canCancelSend = false,
        canRetry = false,
        canLiftBanishment = false,
        reactionEmojis = [] as string[],
        onreply,
        oncopy,
        ontranslate,
        onreact,
        onopenreactionpicker,
        onviewraw,
        ondownloadimage,
        oncopyimage,
        onsavesticker,
        onsavegif,
        oncancelsend,
        onretry,
        onliftbanishment,
        ondelete,
        onclose,
    }: {
        show?: boolean;
        x?: number;
        y?: number;
        justOpened?: boolean;
        openedFromBubble?: boolean;
        canCopy?: boolean;
        canTranslate?: boolean;
        canReact?: boolean;
        hasImage?: boolean;
        canSaveAsGif?: boolean;
        canCancelSend?: boolean;
        canRetry?: boolean;
        canLiftBanishment?: boolean;
        reactionEmojis?: string[];
        onreply?: () => void;
        oncopy?: () => void;
        ontranslate?: () => void;
        onreact?: (emoji: string) => void;
        onopenreactionpicker?: () => void;
        onviewraw?: () => void;
        ondownloadimage?: () => void;
        oncopyimage?: () => void;
        onsavesticker?: () => void;
        onsavegif?: () => void;
        oncancelsend?: () => void;
        onretry?: () => void;
        onliftbanishment?: () => void;
        ondelete?: () => void;
        onclose?: () => void;
    } = $props();

    let panel: HTMLDivElement | undefined = $state();
    let adjustedLeft = $state(0);
    let adjustedTop = $state(0);
    let panelMaxHeight: number | null = $state(null);

    function isReducedMotion(): boolean {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            return false;
        }
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    const transitionDuration = $derived(isReducedMotion() ? 0 : 120);

    async function reposition() {
        await tick();
        if (!panel || !show) return;
        const rect = panel.getBoundingClientRect();
        const result = clampFloatingToViewport(x, y, rect.width, rect.height);
        adjustedLeft = result.left;
        adjustedTop = result.top;
        panelMaxHeight = result.maxHeight;
    }

    $effect(() => {
        if (show) {
            adjustedLeft = x;
            adjustedTop = y;
            panelMaxHeight = null;
            void reposition();
        }
    });

    $effect(() => {
        if (!show) return;
        const onDoc = () => {
            if (!justOpened) onclose?.();
        };
        document.addEventListener("mousedown", onDoc, true);
        return () => document.removeEventListener("mousedown", onDoc, true);
    });
</script>

{#if show}
    <div
        bind:this={panel}
        class="context-menu-panel z-200"
        style="top: {adjustedTop}px; left: {adjustedLeft}px; {panelMaxHeight != null
            ? `max-height: ${panelMaxHeight}px; overflow-y: auto;`
            : ''}"
        role="menu"
        tabindex="-1"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
        transition:fade={{ duration: transitionDuration }}
    >
        <button type="button" class="context-item" role="menuitem" onclick={() => onreply?.()}>
            <MaterialDesignIcon iconName="reply" class="size-4 text-indigo-500" />
            {t("messages.reply")}
        </button>
        {#if openedFromBubble && canCopy}
            <button type="button" class="context-item" role="menuitem" onclick={() => oncopy?.()}>
                <MaterialDesignIcon iconName="content-copy" class="size-4 text-sem-fg-muted" />
                {t("messages.copy_message")}
            </button>
        {/if}
        {#if canTranslate}
            <button type="button" class="context-item" role="menuitem" onclick={() => ontranslate?.()}>
                <MaterialDesignIcon iconName="translate" class="size-4 text-indigo-500" />
                {t("messages.translate_message")}
            </button>
        {/if}
        {#if canReact}
            <div class="px-3 py-2 border-t border-gray-100 dark:border-zinc-700">
                <div class="text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted mb-1.5">
                    {t("messages.react")}
                </div>
                <div class="flex flex-wrap gap-1">
                    {#each reactionEmojis as emo, emi (emi)}
                        <button
                            type="button"
                            class="text-lg leading-none px-1.5 py-0.5 rounded-lg hover:bg-sem-surface-muted transition-colors"
                            title={emo}
                            onclick={() => onreact?.(emo)}
                        >
                            {emo}
                        </button>
                    {/each}
                    <button
                        type="button"
                        class="text-lg leading-none px-1.5 py-0.5 rounded-lg hover:bg-sem-surface-muted transition-colors text-sem-fg-muted"
                        title={t("messages.react")}
                        onclick={() => onopenreactionpicker?.()}
                    >
                        <MaterialDesignIcon iconName="emoticon-plus-outline" class="size-5" />
                    </button>
                </div>
            </div>
        {/if}
        <button type="button" class="context-item" role="menuitem" onclick={() => onviewraw?.()}>
            <MaterialDesignIcon iconName="code-json" class="size-4 text-gray-400" />
            {t("messages.view_raw_lxm")}
        </button>
        {#if hasImage}
            <button type="button" class="context-item" role="menuitem" onclick={() => ondownloadimage?.()}>
                <MaterialDesignIcon iconName="download" class="size-4 text-blue-500" />
                {t("messages.save_image_to_device")}
            </button>
            <button type="button" class="context-item" role="menuitem" onclick={() => oncopyimage?.()}>
                <MaterialDesignIcon iconName="content-copy" class="size-4 text-blue-500" />
                {t("messages.copy_image_to_clipboard")}
            </button>
            <button type="button" class="context-item" role="menuitem" onclick={() => onsavesticker?.()}>
                <MaterialDesignIcon iconName="bookmark-plus-outline" class="size-4 text-teal-500" />
                {t("stickers.save_to_library")}
            </button>
        {/if}
        {#if canSaveAsGif}
            <button type="button" class="context-item" role="menuitem" onclick={() => onsavegif?.()}>
                <MaterialDesignIcon iconName="file-gif-box" class="size-4 text-pink-500" />
                {t("gifs.save_to_library")}
            </button>
        {/if}
        {#if canCancelSend}
            <button
                type="button"
                class="context-item text-amber-600 dark:text-amber-400"
                role="menuitem"
                onclick={() => oncancelsend?.()}
            >
                <MaterialDesignIcon iconName="close-circle-outline" class="size-4" />
                {t("messages.cancel_send")}
            </button>
        {/if}
        {#if canRetry}
            <button
                type="button"
                class="context-item text-amber-600 dark:text-amber-400"
                role="menuitem"
                onclick={() => onretry?.()}
            >
                <MaterialDesignIcon iconName="refresh" class="size-4" />
                {t("messages.retry")}
            </button>
        {/if}
        {#if canLiftBanishment}
            <button
                type="button"
                class="context-item text-emerald-600 dark:text-emerald-400"
                role="menuitem"
                onclick={() => onliftbanishment?.()}
            >
                <MaterialDesignIcon iconName="check-circle" class="size-4" />
                {t("banishment.lift_banishment")}
            </button>
        {/if}
        <div class="context-menu-divider" role="separator"></div>
        <button
            type="button"
            class="context-item text-red-600 dark:text-red-400"
            role="menuitem"
            onclick={() => ondelete?.()}
        >
            <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
            {t("common.delete")}
        </button>
    </div>
{/if}
