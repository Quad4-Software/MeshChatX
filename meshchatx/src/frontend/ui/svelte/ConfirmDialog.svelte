<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import { AlertDialog } from "bits-ui";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface PendingConfirm {
        message: string;
        title: string;
    }

    let pendingConfirm = $state<PendingConfirm | null>(null);
    let resolvePromise = $state<((ok: boolean) => void) | null>(null);
    let open = $state(false);
    let enterIsDown = $state(false);
    let keyboardArmed = $state(false);

    let cancelButton: HTMLButtonElement | undefined = $state();
    let confirmButton: HTMLButtonElement | undefined = $state();

    function isComposingKey(event: KeyboardEvent): boolean {
        return Boolean(event && (event.isComposing || event.keyCode === 229));
    }

    function isTextEntryTarget(target: EventTarget | null): boolean {
        if (!target || typeof target !== "object" || !(target instanceof HTMLElement)) {
            return false;
        }
        const tag = target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") {
            return true;
        }
        return Boolean(target.isContentEditable);
    }

    function focusDefaultButton() {
        confirmButton?.focus();
    }

    function show(payload: { message?: unknown; title?: unknown; resolve?: unknown } = {}) {
        if (typeof resolvePromise === "function") {
            resolvePromise(false);
        }
        const title = typeof payload.title === "string" && payload.title.trim() ? payload.title.trim() : "";
        pendingConfirm = {
            message: payload.message == null ? "" : String(payload.message),
            title,
        };
        resolvePromise = typeof payload.resolve === "function" ? (payload.resolve as (ok: boolean) => void) : null;
        keyboardArmed = !enterIsDown;
        open = true;
    }

    function dismissForOtherDialog() {
        cancel();
    }

    function isCancelTarget(target: EventTarget | null): boolean {
        if (!target || typeof target !== "object" || !(target instanceof HTMLElement)) {
            return false;
        }
        if (cancelButton && (target === cancelButton || cancelButton.contains(target))) {
            return true;
        }
        return Boolean(target.closest("[data-confirm-cancel]"));
    }

    function onWindowKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            enterIsDown = true;
        }
        if (!pendingConfirm || event.key !== "Enter") {
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

    function onWindowKeyup(event: KeyboardEvent) {
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
        open = false;
    }

    function cancel() {
        if (resolvePromise) {
            resolvePromise(false);
            resolvePromise = null;
        }
        pendingConfirm = null;
        keyboardArmed = false;
        open = false;
    }

    function onOpenAutoFocus(event: Event) {
        if (keyboardArmed) {
            event.preventDefault();
            focusDefaultButton();
        }
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

<AlertDialog.Root
    bind:open
    onOpenChange={(next) => {
        if (!next) {
            cancel();
        }
    }}
>
    <AlertDialog.Portal>
        <AlertDialog.Overlay class="fixed inset-0 z-9998 bg-black/50 backdrop-blur-xs" />
        {#if open}
            <div
                class="pointer-events-none fixed inset-0 z-9999 flex items-center justify-center p-4 confirm-dialog-root"
            >
                <AlertDialog.Content
                    class="pointer-events-auto relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-sem-surface rounded-3xl shadow-2xl border border-sem-border overflow-hidden"
                    {onOpenAutoFocus}
                >
                    <div class="p-8">
                        <div class="flex items-start mb-6">
                            <div
                                class="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 mr-4"
                            >
                                <MaterialDesignIcon iconName="alert-circle" />
                            </div>
                            <div class="flex-1 min-w-0">
                                <AlertDialog.Title level={3} class="text-xl font-black text-sem-fg mb-2">
                                    {pendingConfirm?.title || t("common.confirm_action")}
                                </AlertDialog.Title>
                                <AlertDialog.Description class="text-sem-fg-muted whitespace-pre-wrap leading-relaxed">
                                    {pendingConfirm?.message}
                                </AlertDialog.Description>
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
                </AlertDialog.Content>
            </div>
        {/if}
    </AlertDialog.Portal>
</AlertDialog.Root>
