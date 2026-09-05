<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    let {
        deliveryMethod = null as string | null,
        canSendMessage = false,
        isSendingMessage = false,
        compact = false,
        sendingTooltip = "Resolving route to peer (finding path). This can take a while on first contact or after links change. Paths are remembered until they expire.",
        canOpenSendMenu = false,
        onsend,
        ondeliverymethodchanged,
        onsendcommandorrequest,
        onsendpapercompose,
    }: {
        deliveryMethod?: string | null;
        canSendMessage?: boolean;
        isSendingMessage?: boolean;
        compact?: boolean;
        sendingTooltip?: string;
        canOpenSendMenu?: boolean;
        onsend?: () => void;
        ondeliverymethodchanged?: (method: string | null) => void;
        onsendcommandorrequest?: () => void;
        onsendpapercompose?: () => void;
    } = $props();

    let isShowingMenu = $state(false);
    let compactLongPressTimer: number | null = $state(null);
    let compactTapArmed = $state(false);
    let rootEl: HTMLDivElement | undefined = $state();

    const compactTitle = $derived(isSendingMessage ? sendingTooltip : t("messages.send_hold_for_options"));

    function clearCompactLongPressTimer() {
        if (compactLongPressTimer != null) {
            clearTimeout(compactLongPressTimer);
            compactLongPressTimer = null;
        }
    }

    function onCompactPointerDown() {
        if (!compact || (!canSendMessage && !canOpenSendMenu)) return;
        compactTapArmed = true;
        clearCompactLongPressTimer();
        compactLongPressTimer = window.setTimeout(() => {
            compactLongPressTimer = null;
            compactTapArmed = false;
            isShowingMenu = true;
        }, 500);
    }

    function onCompactPointerUp() {
        if (!compact) return;
        clearCompactLongPressTimer();
    }

    function onCompactPointerCancel() {
        if (!compact) return;
        clearCompactLongPressTimer();
        compactTapArmed = false;
    }

    function onCompactClick() {
        if (!compact || !compactTapArmed) return;
        compactTapArmed = false;
        onsend?.();
    }

    function setDeliveryMethod(method: string | null) {
        ondeliverymethodchanged?.(method);
        isShowingMenu = false;
    }

    function toggleSendMenu() {
        if (!canSendMessage && !canOpenSendMenu) return;
        isShowingMenu = !isShowingMenu;
    }

    $effect(() => {
        if (!isShowingMenu) return;
        const onDoc = (event: MouseEvent) => {
            if (rootEl && !rootEl.contains(event.target as Node)) {
                isShowingMenu = false;
            }
        };
        document.addEventListener("mousedown", onDoc, true);
        return () => {
            document.removeEventListener("mousedown", onDoc, true);
            clearCompactLongPressTimer();
        };
    });
</script>

<div bind:this={rootEl} class="relative inline-flex items-stretch rounded-xl shadow-xs">
    {#if compact}
        <button
            disabled={!canSendMessage && !canOpenSendMenu}
            type="button"
            class="inline-flex items-center justify-center rounded-xl p-2.5 min-h-[44px] min-w-[44px] text-white transition-colors focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 touch-manipulation select-none {canSendMessage ||
            canOpenSendMenu
                ? 'bg-sem-action-primary hover:bg-sem-action-primary-hover focus-visible:outline-sem-focus press-feedback'
                : 'bg-sem-fg-muted/40 focus-visible:outline-sem-fg-muted cursor-not-allowed'}"
            title={compactTitle}
            onpointerdown={onCompactPointerDown}
            onpointerup={onCompactPointerUp}
            onpointercancel={onCompactPointerCancel}
            onclick={onCompactClick}
        >
            {#if !isSendingMessage}
                <MaterialDesignIcon iconName="send" class="w-5 h-5" />
            {:else}
                <span class="text-xs font-semibold opacity-90">...</span>
            {/if}
        </button>
    {:else}
        <button
            disabled={!canSendMessage}
            type="button"
            class="inline-flex items-center gap-2 rounded-l-xl px-4 py-2.5 text-sm font-semibold text-white transition-colors focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 {canSendMessage
                ? 'bg-sem-action-primary hover:bg-sem-action-primary-hover focus-visible:outline-sem-focus press-feedback'
                : 'bg-sem-fg-muted/40 focus-visible:outline-sem-fg-muted cursor-not-allowed'}"
            title={isSendingMessage ? sendingTooltip : ""}
            onclick={() => onsend?.()}
        >
            {#if !isSendingMessage}
                <MaterialDesignIcon iconName="send" class="w-4 h-4" />
            {/if}
            <span class={isSendingMessage ? "opacity-60" : ""}>
                {#if deliveryMethod === "direct"}
                    {t("messages.send_direct")}
                {:else if deliveryMethod === "opportunistic"}
                    {t("messages.send_opportunistic")}
                {:else if deliveryMethod === "propagated"}
                    {t("messages.send_propagated")}
                {:else}
                    {t("messages.send")}
                {/if}
            </span>
        </button>
        <div class="relative self-stretch">
            <button
                disabled={!canSendMessage && !canOpenSendMenu}
                type="button"
                class="border-l relative inline-flex items-center justify-center rounded-r-xl px-2.5 h-full text-white transition-colors focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 {canSendMessage ||
                canOpenSendMenu
                    ? 'bg-sem-action-primary hover:bg-sem-action-primary-hover focus-visible:outline-sem-focus border-sem-action-primary-hover press-feedback'
                    : 'bg-sem-fg-muted/40 focus-visible:outline-sem-fg-muted border-sem-border cursor-not-allowed'}"
                aria-label={t("messages.send_hold_for_options")}
                aria-expanded={isShowingMenu}
                title={t("messages.send_hold_for_options")}
                onclick={toggleSendMenu}
            >
                <MaterialDesignIcon
                    iconName="chevron-down"
                    class="h-4 w-4 transition-transform {isShowingMenu ? 'rotate-180' : ''}"
                />
            </button>
        </div>
    {/if}

    {#if isShowingMenu}
        <div
            class="absolute bottom-full right-0 mb-1 z-10 rounded-xl bg-sem-surface shadow-lg ring-1 ring-gray-200 dark:ring-zinc-800 focus:outline-hidden overflow-hidden min-w-[220px]"
        >
            <div class="py-1">
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2 text-sm text-sem-fg hover:bg-sem-surface-muted whitespace-nowrap border-b border-sem-border"
                    onclick={() => setDeliveryMethod(null)}
                >
                    <MaterialDesignIcon iconName="auto-fix" class="size-5 shrink-0 text-sem-fg-muted" />
                    <span>{t("messages.send_automatically")}</span>
                </button>
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2 text-sm text-sem-fg hover:bg-sem-surface-muted whitespace-nowrap"
                    onclick={() => setDeliveryMethod("direct")}
                >
                    <MaterialDesignIcon iconName="transit-connection-variant" class="size-5 shrink-0 text-sem-fg-muted" />
                    <span>{t("messages.send_over_direct_link")}</span>
                </button>
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2 text-sm text-sem-fg hover:bg-sem-surface-muted whitespace-nowrap"
                    onclick={() => setDeliveryMethod("opportunistic")}
                >
                    <MaterialDesignIcon iconName="swap-horizontal" class="size-5 shrink-0 text-sem-fg-muted" />
                    <span>{t("messages.send_opportunistically")}</span>
                </button>
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2 text-sm text-sem-fg hover:bg-sem-surface-muted whitespace-nowrap"
                    onclick={() => setDeliveryMethod("propagated")}
                >
                    <MaterialDesignIcon iconName="access-point-network" class="size-5 shrink-0 text-sem-fg-muted" />
                    <span>{t("messages.send_to_propagation_node")}</span>
                </button>
                <div class="border-t border-sem-border text-[11px] font-medium text-sem-fg-muted px-4 pt-2 pb-1">
                    {t("messages.send_menu_more_label")}
                </div>
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2 text-sm text-sem-fg hover:bg-sem-surface-muted whitespace-nowrap disabled:opacity-50"
                    disabled={!canOpenSendMenu}
                    onclick={() => {
                        onsendcommandorrequest?.();
                        isShowingMenu = false;
                    }}
                >
                    <MaterialDesignIcon iconName="code-tags" class="size-5 shrink-0 text-sem-fg-muted" />
                    <span>{t("messages.send_menu_telemetry_request")}</span>
                </button>
                <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2 text-sm text-sem-fg hover:bg-sem-surface-muted whitespace-nowrap disabled:opacity-50"
                    disabled={!canSendMessage}
                    onclick={() => {
                        onsendpapercompose?.();
                        isShowingMenu = false;
                    }}
                >
                    <MaterialDesignIcon iconName="qrcode" class="size-5 shrink-0 text-sem-fg-muted" />
                    <span>{t("messages.send_menu_paper_compose")}</span>
                </button>
            </div>
        </div>
    {/if}
</div>
