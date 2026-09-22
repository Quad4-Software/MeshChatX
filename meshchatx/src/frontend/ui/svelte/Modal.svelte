<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, tick } from "svelte";
    import type { Snippet } from "svelte";
    import { Dialog } from "bits-ui";
    import { fade, fly } from "svelte/transition";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface Props {
        open?: boolean;
        title?: string;
        persistent?: boolean;
        showClose?: boolean;
        maxWidth?: number | string;
        panelClass?: string;
        bodyClass?: string;
        onClose?: () => void;
        children?: Snippet;
        header?: Snippet;
        footer?: Snippet;
    }

    let {
        open = $bindable(false),
        title = "",
        persistent = false,
        showClose = true,
        maxWidth = 520,
        panelClass = "",
        bodyClass = "overflow-y-auto overscroll-contain",
        onClose,
        children,
        header,
        footer,
    }: Props = $props();

    function isReducedMotion(): boolean {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            return false;
        }
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    const transitionDuration = $derived(isReducedMotion() ? 0 : 150);

    const panelMaxWidth = $derived(
        typeof maxWidth === "number"
            ? `${maxWidth}px`
            : maxWidth.includes("px") || maxWidth.includes("rem") || maxWidth.includes("%")
              ? maxWidth
              : `${maxWidth}px`
    );

    // Modals are opened programmatically (bind:open, no Dialog.Trigger), so
    // record the element that held focus before the dialog took over and give
    // it back on close for WCAG 2.4.3 focus order.
    let previouslyFocused: HTMLElement | null = null;

    $effect.pre(() => {
        if (open) {
            const active = document.activeElement;
            previouslyFocused = active instanceof HTMLElement && active !== document.body ? active : null;
        }
    });

    $effect(() => {
        if (open) return;
        const el = previouslyFocused;
        previouslyFocused = null;
        if (el?.isConnected) {
            void tick().then(() => {
                if (el.isConnected) {
                    el.focus();
                }
            });
        }
    });

    // If the modal is unmounted while still open (keepAlive teardown), the
    // close transition never runs, so restore focus here as well. A normal
    // close clears previouslyFocused first, so this only fires for teardown.
    onDestroy(() => {
        const el = previouslyFocused;
        previouslyFocused = null;
        if (el?.isConnected) {
            el.focus();
        }
    });

    function handleOpenChange(next: boolean) {
        if (!next) {
            onClose?.();
        }
    }

    function guardPersistent(event: Event) {
        if (persistent) {
            event.preventDefault();
        }
    }
</script>

<Dialog.Root bind:open onOpenChange={handleOpenChange}>
    <Dialog.Portal>
        <Dialog.Overlay forceMount class="fixed inset-0 z-200 bg-black/50 backdrop-blur-xs">
            {#snippet child({ props, open: dialogOpen })}
                {#if dialogOpen}
                    <div {...props} transition:fade={{ duration: transitionDuration }}></div>
                {/if}
            {/snippet}
        </Dialog.Overlay>
        <div
            class="pointer-events-none fixed inset-0 z-200 flex items-center justify-center p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))]"
        >
            <Dialog.Content
                forceMount
                class="modal-panel pointer-events-auto flex w-full flex-col {panelClass}"
                style="max-width: {panelMaxWidth}; max-height: min(90dvh, 100%);"
                onEscapeKeydown={guardPersistent}
                onInteractOutside={guardPersistent}
            >
                {#snippet child({ props, open: dialogOpen })}
                    {#if dialogOpen}
                        <div {...props} transition:fly={{ y: 8, duration: transitionDuration }}>
                            {#if header || title || showClose}
                                <div class="modal-panel__header">
                                    {#if header}
                                        {@render header()}
                                    {:else if title}
                                        <Dialog.Title
                                            level={2}
                                            class="min-w-0 flex-1 text-lg font-semibold text-sem-fg"
                                        >
                                            {title}
                                        </Dialog.Title>
                                    {/if}
                                    {#if showClose}
                                        <Dialog.Close
                                            class="icon-btn-muted toolbar-icon-btn shrink-0 ml-auto"
                                            aria-label={t("common.close")}
                                        >
                                            <MaterialDesignIcon iconName="close" class="size-5" />
                                        </Dialog.Close>
                                    {/if}
                                </div>
                            {/if}
                            <div class="min-h-0 flex-1 {bodyClass}">
                                {#if children}
                                    {@render children()}
                                {/if}
                            </div>
                            {#if footer}
                                <div class="modal-panel__footer">
                                    {@render footer()}
                                </div>
                            {/if}
                        </div>
                    {/if}
                {/snippet}
            </Dialog.Content>
        </div>
    </Dialog.Portal>
</Dialog.Root>
