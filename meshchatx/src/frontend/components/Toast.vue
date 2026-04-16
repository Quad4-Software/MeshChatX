<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        <TransitionGroup name="toast">
            <div
                v-for="toast in toasts"
                :key="toast.id"
                class="pointer-events-auto flex items-center p-4 min-w-[300px] max-w-md rounded-xl shadow-lg border backdrop-blur-md transition-all duration-300"
                :class="toastClass(toast.type)"
            >
                <!-- icon -->
                <div class="mr-3 flex-shrink-0">
                    <MaterialDesignIcon
                        v-if="toast.type === 'success'"
                        icon-name="check-circle"
                        class="h-6 w-6 text-green-500"
                    />
                    <MaterialDesignIcon
                        v-else-if="toast.type === 'error'"
                        icon-name="alert-circle"
                        class="h-6 w-6 text-red-500"
                    />
                    <MaterialDesignIcon
                        v-else-if="toast.type === 'warning'"
                        icon-name="alert"
                        class="h-6 w-6 text-amber-500"
                    />
                    <MaterialDesignIcon
                        v-else-if="toast.type === 'loading'"
                        icon-name="loading"
                        class="h-6 w-6 text-blue-500 animate-spin"
                    />
                    <MaterialDesignIcon v-else icon-name="information" class="h-6 w-6 text-blue-500" />
                </div>

                <!-- content -->
                <div class="flex-1 mr-2 text-sm font-medium text-gray-900 dark:text-zinc-100">
                    {{ $t(toast.message) }}
                </div>

                <!-- close button -->
                <button
                    class="ml-auto text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                    @click="remove(toast.id)"
                >
                    <MaterialDesignIcon icon-name="close" class="h-4 w-4" />
                </button>
            </div>
        </TransitionGroup>
    </div>
</template>

<script>
import GlobalEmitter from "../js/GlobalEmitter";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "Toast",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            toasts: [],
            counter: 0,
        };
    },
    mounted() {
        this.toastHandler = (toast) => {
            this.add(toast);
        };
        this.dismissHandler = ({ key }) => {
            if (key == null) {
                return;
            }
            const index = this.toasts.findIndex((t) => t.key === key);
            if (index !== -1) {
                this.remove(this.toasts[index].id);
            }
        };
        GlobalEmitter.on("toast", this.toastHandler);
        GlobalEmitter.on("toast-dismiss", this.dismissHandler);
    },
    beforeUnmount() {
        GlobalEmitter.off("toast", this.toastHandler);
        GlobalEmitter.off("toast-dismiss", this.dismissHandler);
    },
    methods: {
        add(toast) {
            // Check if a toast with the same key already exists
            if (toast.key) {
                const existingIndex = this.toasts.findIndex((t) => t.key === toast.key);
                if (existingIndex !== -1) {
                    const existingToast = this.toasts[existingIndex];

                    // Clear existing timeout if it exists
                    if (existingToast.timer) {
                        clearTimeout(existingToast.timer);
                    }

                    // Update existing toast
                    existingToast.message = toast.message;
                    existingToast.type = toast.type || "info";
                    existingToast.duration = toast.duration !== undefined ? toast.duration : 5000;

                    if (existingToast.duration > 0) {
                        existingToast.timer = setTimeout(() => {
                            this.remove(existingToast.id);
                        }, existingToast.duration);
                    } else {
                        existingToast.timer = null;
                    }
                    return;
                }
            }

            const id = this.counter++;
            const newToast = {
                id,
                key: toast.key,
                message: toast.message,
                type: toast.type || "info",
                duration: toast.duration !== undefined ? toast.duration : 5000,
                timer: null,
            };

            if (newToast.duration > 0) {
                newToast.timer = setTimeout(() => {
                    this.remove(id);
                }, newToast.duration);
            }

            this.toasts.push(newToast);
        },
        remove(id) {
            const index = this.toasts.findIndex((t) => t.id === id);
            if (index !== -1) {
                const toast = this.toasts[index];
                if (toast.timer) {
                    clearTimeout(toast.timer);
                }
                this.toasts.splice(index, 1);
            }
        },
        toastClass(type) {
            switch (type) {
                case "success":
                    return "bg-white/90 dark:bg-zinc-900/90 border-green-500/30";
                case "error":
                    return "bg-white/90 dark:bg-zinc-900/90 border-red-500/30";
                case "warning":
                    return "bg-white/90 dark:bg-zinc-900/90 border-amber-500/30";
                default:
                    return "bg-white/90 dark:bg-zinc-900/90 border-blue-500/30";
            }
        },
    },
};
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
    transition: all 0.3s ease;
}
.toast-enter-from {
    opacity: 0;
    transform: translateX(30px);
}
.toast-leave-to {
    opacity: 0;
    transform: translateX(30px);
}
</style>
