<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Transition name="confirm-dialog">
        <div v-if="pendingConfirm" class="fixed inset-0 z-[9999] flex items-center justify-center p-4">
            <div class="fixed inset-0 bg-black/50 backdrop-blur-sm shadow-2xl" @click="cancel"></div>

            <div
                class="relative w-full sm:w-auto sm:min-w-[400px] sm:max-w-md bg-white dark:bg-zinc-900 sm:rounded-3xl rounded-3xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden transform transition-all"
                @click.stop
            >
                <div class="p-8">
                    <div class="flex items-start mb-6">
                        <div
                            class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 mr-4"
                        >
                            <MaterialDesignIcon icon-name="alert-circle" class="w-6 h-6" />
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 class="text-xl font-black text-gray-900 dark:text-white mb-2">Confirm Action</h3>
                            <p class="text-gray-600 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed">
                                {{ pendingConfirm.message }}
                            </p>
                        </div>
                    </div>

                    <div class="flex flex-col sm:flex-row gap-3 sm:justify-end mt-8">
                        <button
                            type="button"
                            class="px-6 py-3 text-sm font-bold text-gray-700 dark:text-zinc-300 bg-gray-100 dark:bg-zinc-800 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all active:scale-95"
                            @click="cancel"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            class="px-6 py-3 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl shadow-lg shadow-red-600/20 transition-all active:scale-95"
                            @click="confirm"
                        >
                            Confirm
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
    name: "ConfirmDialog",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            pendingConfirm: null,
            resolvePromise: null,
        };
    },
    mounted() {
        GlobalEmitter.on("confirm", this.show);
    },
    beforeUnmount() {
        GlobalEmitter.off("confirm", this.show);
    },
    methods: {
        show({ message, resolve }) {
            this.pendingConfirm = { message };
            this.resolvePromise = resolve;
        },
        confirm() {
            if (this.resolvePromise) {
                this.resolvePromise(true);
                this.resolvePromise = null;
            }
            this.pendingConfirm = null;
        },
        cancel() {
            if (this.resolvePromise) {
                this.resolvePromise(false);
                this.resolvePromise = null;
            }
            this.pendingConfirm = null;
        },
    },
};
</script>

<style scoped>
.confirm-dialog-enter-active,
.confirm-dialog-leave-active {
    transition: all 0.2s ease;
}

.confirm-dialog-enter-from,
.confirm-dialog-leave-to {
    opacity: 0;
}

.confirm-dialog-enter-from .relative,
.confirm-dialog-leave-to .relative {
    transform: scale(0.95);
    opacity: 0;
}
</style>
