<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
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

    const titleId =
        "modal-title-" +
        (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
            ? crypto.randomUUID()
            : Math.random().toString(36).slice(2, 11));

    let panelElement: HTMLElement | undefined;
    let previousActiveElement: HTMLElement | null = null;

    const FOCUSABLE_SELECTOR =
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

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

    function close() {
        open = false;
        if (onClose) {
            onClose();
        }
    }

    function onBackdropClick(event: MouseEvent) {
        if (!persistent && event.target === event.currentTarget) {
            close();
        }
    }

    function focusInitialElement(node: HTMLElement) {
        const nodes = node.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
        const list = Array.from(nodes).filter((el) => !el.hasAttribute("disabled") && el.tabIndex !== -1);
        if (list.length > 0) {
            list[0].focus();
        } else {
            node.focus();
        }
    }

    function trapFocus(event: KeyboardEvent) {
        if (!panelElement) {
            return;
        }
        const nodes = panelElement.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
        const list = Array.from(nodes).filter((el) => !el.hasAttribute("disabled") && el.tabIndex !== -1);
        if (list.length === 0) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        const first = list[0];
        const last = list[list.length - 1];
        const active = document.activeElement;
        if (event.shiftKey && (active === first || !panelElement.contains(active))) {
            event.preventDefault();
            event.stopPropagation();
            last.focus();
            return;
        }
        if (!event.shiftKey && (active === last || !panelElement.contains(active))) {
            event.preventDefault();
            event.stopPropagation();
            first.focus();
        }
    }

    function onWindowKeydown(event: KeyboardEvent) {
        if (!open) {
            return;
        }
        if (event.key === "Escape") {
            if (!persistent) {
                event.preventDefault();
                event.stopPropagation();
                close();
            }
            return;
        }
        if (event.key === "Tab") {
            trapFocus(event);
        }
    }

    function modalPanelAction(node: HTMLElement) {
        panelElement = node;
        if (typeof document !== "undefined" && document.activeElement instanceof HTMLElement) {
            previousActiveElement = document.activeElement;
        }
        focusInitialElement(node);

        return {
            destroy() {
                if (previousActiveElement && typeof previousActiveElement.focus === "function") {
                    previousActiveElement.focus();
                }
                previousActiveElement = null;
                panelElement = undefined;
            },
        };
    }
</script>

<svelte:window onkeydown={onWindowKeydown} />

{#if open}
    <div
        class="fixed inset-0 z-200 flex items-center justify-center p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] bg-black/50 backdrop-blur-xs"
        onclick={onBackdropClick}
        role="presentation"
        transition:fade={{ duration: transitionDuration }}
    >
        <div
            use:modalPanelAction
            class="modal-panel flex w-full flex-col {panelClass}"
            style="max-width: {panelMaxWidth}; max-height: min(90dvh, 100%);"
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? titleId : undefined}
            tabindex="-1"
            transition:fly={{ y: 8, duration: transitionDuration }}
        >
            {#if header || title || showClose}
                <div class="modal-panel__header">
                    {#if header}
                        {@render header()}
                    {:else if title}
                        <h2 id={titleId} class="min-w-0 flex-1 text-lg font-semibold text-sem-fg">
                            {title}
                        </h2>
                    {/if}
                    {#if showClose}
                        <button
                            type="button"
                            class="icon-btn-muted toolbar-icon-btn shrink-0 ml-auto"
                            aria-label={t("common.close")}
                            onclick={close}
                        >
                            <MaterialDesignIcon iconName="close" class="size-5" />
                        </button>
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
    </div>
{/if}
