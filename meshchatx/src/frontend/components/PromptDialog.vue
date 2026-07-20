<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Transition name="prompt-dialog">
        <div v-if="pendingPrompt" class="fixed inset-0 z-9999 flex items-center justify-center p-4">
            <div class="fixed inset-0 bg-black/50 backdrop-blur-xs shadow-2xl" @click="cancel"></div>

            <div
                class="relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-white dark:bg-zinc-900 sm:rounded-3xl rounded-3xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden transform transition-all"
                @click.stop
            >
                <div class="p-8">
                    <div class="flex items-start mb-6">
                        <div
                            class="shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 mr-4"
                        >
                            <MaterialDesignIcon icon-name="form-textbox" class="w-6 h-6" />
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 class="text-xl font-black text-gray-900 dark:text-white mb-2">
                                {{ $t("common.prompt_title") }}
                            </h3>
                            <p class="text-gray-600 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">
                                {{ pendingPrompt.message }}
                            </p>
                        </div>
                    </div>

                    <input
                        ref="promptInput"
                        v-model="inputValue"
                        :type="inputType"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
                        autocomplete="off"
                        @keydown.enter.prevent="confirm"
                        @keydown.esc.prevent="cancel"
                    />

                    <div class="flex flex-col sm:flex-row gap-3 sm:justify-end mt-8">
                        <button
                            type="button"
                            class="px-6 py-3 text-sm font-bold text-gray-700 dark:text-zinc-300 bg-gray-100 dark:bg-zinc-800 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all active:scale-95"
                            @click="cancel"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                        <button
                            type="button"
                            class="px-6 py-3 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-600/20 transition-all active:scale-95"
                            @click="confirm"
                        >
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
        };
    },
    mounted() {
        GlobalEmitter.on("prompt", this.show);
    },
    beforeUnmount() {
        GlobalEmitter.off("prompt", this.show);
    },
    methods: {
        show({ message, defaultValue, resolve, inputType }) {
            this.pendingPrompt = { message };
            this.inputValue = defaultValue == null ? "" : String(defaultValue);
            this.inputType = inputType === "password" ? "password" : "text";
            this.resolvePromise = resolve;
            this.$nextTick(() => {
                const input = this.$refs.promptInput;
                if (input && typeof input.focus === "function") {
                    input.focus();
                    input.select();
                }
            });
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
