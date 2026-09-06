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

<script>
import GlobalEmitter from "../js/GlobalEmitter";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

function isComposingKey(event) {
    return Boolean(event && (event.isComposing || event.keyCode === 229));
}

export default {
    name: "PromptDialog",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            pendingPrompt: null,
            resolvePromise: null,
            inputValue: "",
            inputType: "text",
            titleId: "prompt-dialog-title",
            messageId: "prompt-dialog-message",
        };
    },
    mounted() {
        GlobalEmitter.on("prompt", this.show);
        GlobalEmitter.on("confirm", this.dismissForOtherDialog);
        window.addEventListener("keydown", this.onWindowKeydown, true);
    },
    beforeUnmount() {
        this.cancel();
        GlobalEmitter.off("prompt", this.show);
        GlobalEmitter.off("confirm", this.dismissForOtherDialog);
        window.removeEventListener("keydown", this.onWindowKeydown, true);
    },
    methods: {
        show({ message, defaultValue, resolve, inputType } = {}) {
            if (typeof this.resolvePromise === "function") {
                this.resolvePromise(null);
            }
            this.pendingPrompt = { message: message == null ? "" : String(message) };
            this.inputValue = defaultValue == null ? "" : String(defaultValue);
            this.inputType = inputType === "password" ? "password" : "text";
            this.resolvePromise = typeof resolve === "function" ? resolve : null;
            this.$nextTick(() => {
                const input = this.$refs.promptInput;
                if (input && typeof input.focus === "function") {
                    input.focus();
                    input.select();
                }
            });
        },
        dismissForOtherDialog() {
            this.cancel();
        },
        onInputKeydown(event) {
            if (event.key === "Escape") {
                event.preventDefault();
                this.cancel();
                return;
            }
            if (event.key !== "Enter") {
                return;
            }
            if (isComposingKey(event)) {
                return;
            }
            event.preventDefault();
            this.confirm();
        },
        onWindowKeydown(event) {
            if (!this.pendingPrompt) {
                return;
            }
            if (event.key !== "Escape") {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            this.cancel();
        },
        confirm() {
            if (this.resolvePromise) {
                this.resolvePromise(this.inputValue);
                this.resolvePromise = null;
            }
            this.pendingPrompt = null;
            this.inputValue = "";
            this.inputType = "text";
        },
        cancel() {
            if (this.resolvePromise) {
                this.resolvePromise(null);
                this.resolvePromise = null;
            }
            this.pendingPrompt = null;
            this.inputValue = "";
            this.inputType = "text";
        },
    },
};
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
