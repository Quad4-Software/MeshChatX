<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="fixed max-sm:bottom-[calc(1rem+env(safe-area-inset-bottom,0px))] bottom-4 left-1/2 -translate-x-1/2 sm:left-auto sm:right-4 sm:translate-x-0 z-100 flex flex-col gap-2 pointer-events-none w-[calc(100%-2rem)] max-w-sm sm:w-auto sm:max-w-md"
    >
        <TransitionGroup name="toast">
            <div
                v-for="toast in toasts"
                :key="toast.id"
                ref="toastRefs"
                class="pointer-events-auto flex items-center p-4 w-full sm:min-w-[300px] sm:max-w-md rounded-xl shadow-lg border backdrop-blur-md transition-all duration-300 select-none touch-pan-y"
                :class="[toastClass(toast.type), toast.swipeClass]"
                :style="toastSwipeStyle(toast)"
                @touchstart="onTouchStart($event, toast)"
                @touchmove="onTouchMove($event, toast)"
                @touchend="onTouchEnd(toast)"
                @touchcancel="onTouchEnd(toast)"
            >
                <!-- icon -->
                <div class="mr-3 shrink-0">
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
            swipeThreshold: 100,
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
                _swipeX: 0,
                _swiping: false,
                swipeClass: "",
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
        toastSwipeStyle(toast) {
            const x = toast._swipeX || 0;
            if (x === 0) return {};
            return {
                transform: `translateX(${x}px)`,
                transition: toast._swiping ? "none" : "transform 0.3s ease",
                opacity: `${1 - Math.min(Math.abs(x) / this.swipeThreshold, 0.6)}`,
            };
        },
        onTouchStart(event, toast) {
            if (event.touches.length !== 1) return;
            toast._startX = event.touches[0].clientX;
            toast._swipeX = 0;
            toast._swiping = true;
            toast.swipeClass = "";
        },
        onTouchMove(event, toast) {
            if (!toast._swiping || event.touches.length !== 1) return;
            const deltaX = event.touches[0].clientX - toast._startX;
            toast._swipeX = deltaX;
        },
        onTouchEnd(toast) {
            if (!toast._swiping) return;
            toast._swiping = false;
            if (Math.abs(toast._swipeX) >= this.swipeThreshold) {
                toast.swipeClass = toast._swipeX > 0 ? "toast-swipe-out-right" : "toast-swipe-out-left";
                this.$nextTick(() => {
                    setTimeout(() => this.remove(toast.id), 250);
                });
            } else {
                toast._swipeX = 0;
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
    transform: translateY(30px);
}
.toast-leave-to {
    opacity: 0;
    transform: translateY(30px);
}
@media (min-width: 640px) {
    .toast-enter-from {
        transform: translateX(30px);
    }
    .toast-leave-to {
        transform: translateX(30px);
    }
}
.toast-swipe-out-left {
    transform: translateX(-120%) !important;
    opacity: 0 !important;
    transition:
        transform 0.25s ease,
        opacity 0.25s ease !important;
}
.toast-swipe-out-right {
    transform: translateX(120%) !important;
    opacity: 0 !important;
    transition:
        transform 0.25s ease,
        opacity 0.25s ease !important;
}
</style>
