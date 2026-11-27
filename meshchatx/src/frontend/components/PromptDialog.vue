<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Transition name="prompt-dialog">
        <div
            v-if="pendingPrompt"
            class="fixed inset-0 z-9999 flex items-center justify-center p-4"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="titleId"
            :aria-describedby="messageId"
        >
            <div class="fixed inset-0 bg-black/50 backdrop-blur-xs shadow-2xl" @click="cancel"></div>

            <div
                class="relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-sem-surface sm:rounded-3xl rounded-3xl shadow-2xl border border-sem-border overflow-hidden transform transition-all"
                @click.stop
            >
                <div class="p-8">
                    <div class="flex items-start mb-6">
                        <div
                            class="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-sem-info/15 text-sem-accent mr-4"
                        >
                            <MaterialDesignIcon icon-name="form-textbox" class="w-6 h-6" />
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 :id="titleId" class="text-xl font-black text-sem-fg mb-2">
                                {{ $t("common.prompt_title") }}
                            </h3>
                            <p :id="messageId" class="text-sem-fg-muted whitespace-pre-wrap leading-relaxed">
                                {{ pendingPrompt.message }}
                            </p>
                        </div>
                    </div>

                    <input
                        ref="promptInput"
                        v-model="inputValue"
                        :type="inputType"
                        class="w-full px-4 py-3 rounded-xl border border-sem-border bg-sem-surface-muted text-sem-fg text-sm focus:outline-hidden focus:ring-2 focus:ring-sem-focus/30 focus:border-sem-focus"
                        autocomplete="off"
                        @keydown="onInputKeydown"
                    />

                    <div class="flex flex-col sm:flex-row gap-3 sm:justify-end mt-8">
                        <button type="button" class="secondary-action" @click="cancel">
                            {{ $t("common.cancel") }}
                        </button>
                        <button type="button" class="primary-action" @click="confirm">
                            {{ $t("common.ok") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import GlobalEmitter from "../js/GlobalEmitter";
import { EMITTER_EVENTS } from "../js/constants";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

function isComposingKey(event: KeyboardEvent) {
    return Boolean(event && (event.isComposing || event.keyCode === 229));
}

const pendingPrompt = ref<{ message: string } | null>(null);
const inputValue = ref("");
const inputType = ref("text");
const titleId = "prompt-dialog-title";
const messageId = "prompt-dialog-message";

let resolvePromise: ((value: string | null) => void) | null = null;

const promptInput = ref<HTMLInputElement | null>(null);

onMounted(() => {
    GlobalEmitter.on(EMITTER_EVENTS.PROMPT, show);
    GlobalEmitter.on(EMITTER_EVENTS.CONFIRM, dismissForOtherDialog);
    window.addEventListener("keydown", onWindowKeydown, true);
});

onBeforeUnmount(() => {
    cancel();
    GlobalEmitter.off(EMITTER_EVENTS.PROMPT, show);
    GlobalEmitter.off(EMITTER_EVENTS.CONFIRM, dismissForOtherDialog);
    window.removeEventListener("keydown", onWindowKeydown, true);
});

function show(payload: any = {}) {
    if (payload && typeof payload === "object") {
        payload.handled = true;
    }
    const { message, defaultValue, resolve, inputType: type } = payload;
    if (typeof resolvePromise === "function") {
        resolvePromise(null);
    }
    pendingPrompt.value = { message: message == null ? "" : String(message) };
    inputValue.value = defaultValue == null ? "" : String(defaultValue);
    inputType.value = type === "password" ? "password" : "text";
    resolvePromise = typeof resolve === "function" ? resolve : null;
    nextTick(() => {
        const input = promptInput.value;
        if (input && typeof input.focus === "function") {
            input.focus();
            input.select();
        }
    });
}

function dismissForOtherDialog() {
    cancel();
}

function onInputKeydown(event: KeyboardEvent) {
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

function onWindowKeydown(event: KeyboardEvent) {
    if (!pendingPrompt.value) {
        return;
    }
    if (event.key !== "Escape") {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    cancel();
}

function confirm() {
    if (resolvePromise) {
        resolvePromise(inputValue.value);
        resolvePromise = null;
    }
    pendingPrompt.value = null;
    inputValue.value = "";
    inputType.value = "text";
}

function cancel() {
    if (resolvePromise) {
        resolvePromise(null);
        resolvePromise = null;
    }
    pendingPrompt.value = null;
    inputValue.value = "";
    inputType.value = "text";
}
</script>

<style scoped>
.prompt-dialog-enter-active,
.prompt-dialog-leave-active {
    transition: all 0.2s ease;
}

.prompt-dialog-enter-from,
.prompt-dialog-leave-to {
    opacity: 0;
}

.prompt-dialog-enter-from .relative,
.prompt-dialog-leave-to .relative {
    transform: scale(0.95);
    opacity: 0;
}
</style>
