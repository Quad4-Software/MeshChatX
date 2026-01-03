<template>
    <Transition name="confirm-dialog">
        <div v-if="pendingConfirm" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
            <div
                class="fixed inset-0 bg-black/50 backdrop-blur-sm sm:bg-transparent sm:backdrop-blur-none"
                @click="cancel"
            ></div>

            <div
                class="relative w-full sm:w-auto sm:min-w-[360px] sm:max-w-md bg-white dark:bg-zinc-900 sm:rounded-lg rounded-2xl sm:shadow-lg shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden transform transition-all"
                @click.stop
            >
                <div class="p-4 sm:p-4">
                    <div class="flex items-start mb-4 sm:mb-3">
                        <div
                            class="flex-shrink-0 flex items-center justify-center w-9 h-9 sm:w-7 sm:h-7 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 mr-3 sm:mr-2.5"
                        >
                            <MaterialDesignIcon icon-name="alert-circle" class="w-5 h-5 sm:w-4 sm:h-4" />
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 class="text-base sm:text-sm font-semibold text-gray-900 dark:text-white mb-1.5 sm:mb-1">
                                Confirm
                            </h3>
                            <p
                                class="text-sm sm:text-xs text-gray-600 dark:text-zinc-300 whitespace-pre-wrap leading-relaxed"
                            >
                                {{ pendingConfirm.message }}
                            </p>
                        </div>
                    </div>

                    <div class="flex flex-col-reverse sm:flex-row gap-2 sm:gap-2 sm:justify-end mt-5 sm:mt-3">
                        <button
                            type="button"
                            class="px-4 py-2 sm:px-3 sm:py-1.5 text-sm sm:text-xs font-medium text-gray-700 dark:text-zinc-300 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
                            @click="cancel"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            class="px-4 py-2 sm:px-3 sm:py-1.5 text-sm sm:text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
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
