<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick } from "svelte";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface PromptPayload {
        message?: unknown;
        defaultValue?: unknown;
        resolve?: (value: string | null) => void;
        inputType?: string;
    }

    interface PendingPrompt {
        message: string;
    }

    let pendingPrompt = $state<PendingPrompt | null>(null);
    let resolvePromise: ((value: string | null) => void) | null = null;
    let inputValue = $state("");
    let inputType = $state<"text" | "password">("text");
    let inputElement: HTMLInputElement | undefined = $state();

    const titleId = "prompt-dialog-title";
    const messageId = "prompt-dialog-message";

    function isComposingKey(event: KeyboardEvent): boolean {
        return Boolean(event && (event.isComposing || event.keyCode === 229));
    }

    function show(payload: PromptPayload = {}): void {
        if (typeof resolvePromise === "function") {
            resolvePromise(null);
        }
        pendingPrompt = {
            message: payload.message == null ? "" : String(payload.message),
        };
        inputValue = payload.defaultValue == null ? "" : String(payload.defaultValue);
        inputType = payload.inputType === "password" ? "password" : "text";
        resolvePromise = typeof payload.resolve === "function" ? payload.resolve : null;

        void tick().then(() => {
            if (inputElement && typeof inputElement.focus === "function") {
                inputElement.focus();
                inputElement.select();
            }
        });
    }

    function dismissForOtherDialog(): void {
        cancel();
    }

    function confirm(): void {
        if (resolvePromise) {
            resolvePromise(inputValue);
            resolvePromise = null;
        }
        pendingPrompt = null;
        inputValue = "";
        inputType = "text";
    }

    function cancel(): void {
        if (resolvePromise) {
            resolvePromise(null);
            resolvePromise = null;
        }
        pendingPrompt = null;
        inputValue = "";
        inputType = "text";
    }

    function onInputKeydown(event: KeyboardEvent): void {
        if (event.key === "Escape") {
            event.preventDefault();
            cancel();
            return;
        }
        if (event.key !== "Enter") {
            return;
        }
        if (isComposingKey(event)) {
            return;
        }
        event.preventDefault();
        confirm();
    }

    function onWindowKeydown(event: KeyboardEvent): void {
        if (!pendingPrompt) {
            return;
        }
        if (event.key !== "Escape") {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        cancel();
    }

    onMount(() => {
        const handlePrompt = (payload: unknown) => {
            if (payload && typeof payload === "object") {
                show(payload as PromptPayload);
            }
        };
        GlobalEmitter.on("prompt", handlePrompt);
        GlobalEmitter.on("confirm", dismissForOtherDialog);
        window.addEventListener("keydown", onWindowKeydown, true);

        return () => {
            cancel();
            GlobalEmitter.off("prompt", handlePrompt);
            GlobalEmitter.off("confirm", dismissForOtherDialog);
            window.removeEventListener("keydown", onWindowKeydown, true);
        };
    });
</script>

{#if pendingPrompt}
    <div
        class="fixed inset-0 z-9999 flex items-center justify-center p-4"
        role="dialog"
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
            class="relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-sem-surface sm:rounded-3xl rounded-3xl shadow-2xl border border-sem-border overflow-hidden transform transition-all"
        >
            <div class="p-8">
                <div class="flex items-start mb-6">
                    <div
                        class="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-100 dark:bg-blue-900/30 text-sem-accent mr-4"
                    >
                        <MaterialDesignIcon iconName="form-textbox" class="w-6 h-6" />
                    </div>
                    <div class="flex-1 min-w-0">
                        <h3 id={titleId} class="text-xl font-black text-sem-fg mb-2">
                            {t("common.prompt_title")}
                        </h3>
                        <p id={messageId} class="text-sem-fg-muted whitespace-pre-wrap leading-relaxed">
                            {pendingPrompt.message}
                        </p>
                    </div>
                </div>

                <input
                    bind:this={inputElement}
                    bind:value={inputValue}
                    type={inputType}
                    class="w-full px-4 py-3 rounded-xl border border-sem-border bg-gray-50 dark:bg-zinc-800 text-sem-fg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
                    autocomplete="off"
                    onkeydown={onInputKeydown}
                />

                <div class="flex flex-col sm:flex-row gap-3 sm:justify-end mt-8">
                    <button
                        type="button"
                        class="px-6 py-3 text-sm font-bold text-sem-fg-muted bg-sem-surface-muted rounded-xl hover:bg-gray-200 hover:bg-sem-surface-muted transition-all active:scale-95"
                        onclick={cancel}
                    >
                        {t("common.cancel")}
                    </button>
                    <button
                        type="button"
                        class="px-6 py-3 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-600/20 transition-all active:scale-95"
                        onclick={confirm}
                    >
                        {t("common.ok")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
