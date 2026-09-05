<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import { onMount } from "svelte";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    /** @type {{ message: string, title: string } | null} */
    let pendingConfirm = $state(null);
    /** @type {((ok: boolean) => void) | null} */
    let resolvePromise = $state(null);
    let enterIsDown = $state(false);
    let keyboardArmed = $state(false);

    const titleId = "confirm-dialog-title";
    const messageId = "confirm-dialog-message";

    /** @type {HTMLElement | undefined} */
    let dialogPanel = $state();
    /** @type {HTMLButtonElement | undefined} */
    let cancelButton = $state();
    /** @type {HTMLButtonElement | undefined} */
    let confirmButton = $state();

    function isComposingKey(event) {
        return Boolean(event && (event.isComposing || event.keyCode === 229));
    }

    function isTextEntryTarget(target) {
        if (!target || typeof target !== "object") {
            return false;
        }
        const tag = String(target.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") {
            return true;
        }
        return Boolean(target.isContentEditable);
    }

    function focusDefaultButton() {
        if (confirmButton && typeof confirmButton.focus === "function") {
            confirmButton.focus();
        }
    }

    /**
     * @param {{ message?: unknown, title?: unknown, resolve?: unknown }} [payload]
     */
    function show(payload = {}) {
        if (typeof resolvePromise === "function") {
            resolvePromise(false);
        }
        const title = typeof payload.title === "string" && payload.title.trim() ? payload.title.trim() : "";
        pendingConfirm = {
            message: payload.message == null ? "" : String(payload.message),
            title,
        };
        resolvePromise = typeof payload.resolve === "function" ? payload.resolve : null;
        keyboardArmed = !enterIsDown;
        queueMicrotask(() => {
            if (keyboardArmed) {
                focusDefaultButton();
                return;
            }
            if (dialogPanel && typeof dialogPanel.focus === "function") {
                dialogPanel.focus();
            }
        });
    }

    function dismissForOtherDialog() {
        cancel();
    }

    function isCancelTarget(target) {
        if (!target || typeof target !== "object") {
            return false;
        }
        if (cancelButton && target === cancelButton) {
            return true;
        }
        if (
            cancelButton &&
            typeof target.nodeType === "number" &&
            typeof cancelButton.contains === "function" &&
            cancelButton.contains(target)
        ) {
            return true;
        }
        return typeof target.closest === "function" && Boolean(target.closest("[data-confirm-cancel]"));
    }

    function trapFocus(event) {
        if (!dialogPanel) {
            return;
        }
        const nodes = dialogPanel.querySelectorAll("button");
        const list = Array.from(nodes).filter((el) => !el.disabled);
        if (list.length === 0) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        const first = list[0];
        const last = list[list.length - 1];
        const active = document.activeElement;
        if (event.shiftKey && (active === first || !dialogPanel.contains(active))) {
            event.preventDefault();
            event.stopPropagation();
            last.focus();
            return;
        }
        if (!event.shiftKey && (active === last || !dialogPanel.contains(active))) {
            event.preventDefault();
            event.stopPropagation();
            first.focus();
        }
    }

    function onWindowKeydown(event) {
        if (event.key === "Enter") {
            enterIsDown = true;
        }
        if (!pendingConfirm) {
            return;
        }
        if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            cancel();
            return;
        }
        if (event.key === "Tab") {
            trapFocus(event);
            return;
        }
        if (event.key !== "Enter") {
            return;
        }
        if (!keyboardArmed || event.repeat || isComposingKey(event)) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }
        if (isCancelTarget(event.target) || isTextEntryTarget(event.target)) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        confirm();
    }

    function onWindowKeyup(event) {
        if (event.key !== "Enter") {
            return;
        }
        enterIsDown = false;
        if (pendingConfirm && !keyboardArmed) {
            keyboardArmed = true;
            focusDefaultButton();
        }
    }

    function confirm() {
        if (resolvePromise) {
            resolvePromise(true);
            resolvePromise = null;
        }
        pendingConfirm = null;
        keyboardArmed = false;
    }

    function cancel() {
        if (resolvePromise) {
            resolvePromise(false);
            resolvePromise = null;
        }
        pendingConfirm = null;
        keyboardArmed = false;
    }

    onMount(() => {
        GlobalEmitter.on("confirm", show);
        GlobalEmitter.on("prompt", dismissForOtherDialog);
        window.addEventListener("keydown", onWindowKeydown, true);
        window.addEventListener("keyup", onWindowKeyup, true);
        return () => {
            cancel();
            GlobalEmitter.off("confirm", show);
            GlobalEmitter.off("prompt", dismissForOtherDialog);
            window.removeEventListener("keydown", onWindowKeydown, true);
            window.removeEventListener("keyup", onWindowKeyup, true);
        };
    });
</script>

{#if pendingConfirm}
    <div
        class="fixed inset-0 z-9999 flex items-center justify-center p-4 confirm-dialog-root"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
    >
        <button
            type="button"
            class="fixed inset-0 bg-black/50 backdrop-blur-xs shadow-2xl border-0"
            aria-label={t("common.cancel")}
            onclick={cancel}
        ></button>

        <div
            bind:this={dialogPanel}
            role="document"
            class="relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-sem-surface sm:rounded-3xl rounded-3xl shadow-2xl border border-sem-border overflow-hidden transform transition-all"
            tabindex="-1"
        >
            <div class="p-8">
                <div class="flex items-start mb-6">
                    <div
                        class="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 mr-4"
                    >
                        <MaterialDesignIcon iconName="alert-circle" />
                    </div>
                    <div class="flex-1 min-w-0">
                        <h3 id={titleId} class="text-xl font-black text-sem-fg mb-2">
                            {pendingConfirm.title || t("common.confirm_action")}
                        </h3>
                        <p id={messageId} class="text-sem-fg-muted whitespace-pre-wrap leading-relaxed">
                            {pendingConfirm.message}
                        </p>
                    </div>
                </div>

                <div class="flex flex-col sm:flex-row gap-3 sm:justify-end mt-8">
                    <button
                        bind:this={cancelButton}
                        type="button"
                        data-confirm-cancel
                        class="px-6 py-3 text-sm font-bold text-sem-fg-muted bg-sem-surface-muted rounded-xl hover:bg-gray-200 hover:bg-sem-surface-muted transition-all active:scale-95"
                        onclick={cancel}
                    >
                        {t("common.cancel")}
                    </button>
                    <button
                        bind:this={confirmButton}
                        type="button"
                        class="px-6 py-3 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl shadow-lg shadow-red-600/20 transition-all active:scale-95"
                        onclick={confirm}
                    >
                        {t("common.confirm")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
