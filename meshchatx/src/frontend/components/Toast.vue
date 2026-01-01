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
                    <MaterialDesignIcon v-else icon-name="information" class="h-6 w-6 text-blue-500" />
                </div>

                <!-- content -->
                <div class="flex-1 mr-2 text-sm font-medium text-gray-900 dark:text-zinc-100">
                    {{ toast.message }}
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
        GlobalEmitter.on("toast", (toast) => {
            this.add(toast);
        });
    },
    beforeUnmount() {
        GlobalEmitter.off("toast");
    },
    methods: {
        add(toast) {
            const id = this.counter++;
            const newToast = {
                id,
                message: toast.message,
                type: toast.type || "info",
                duration: toast.duration || 5000,
            };
            this.toasts.push(newToast);

            if (newToast.duration > 0) {
                setTimeout(() => {
                    this.remove(id);
                }, newToast.duration);
            }
        },
        remove(id) {
            const index = this.toasts.findIndex((t) => t.id === id);
            if (index !== -1) {
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
