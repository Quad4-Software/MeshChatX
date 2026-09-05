<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "./MaterialDesignIcon.svelte";

    interface ToastItem {
        id: number;
        key?: string | number | null;
        message: string;
        details: string[];
        type: "success" | "error" | "warning" | "loading" | "info";
        duration: number;
        timer: ReturnType<typeof setTimeout> | null;
        _startX?: number;
        _swipeX?: number;
        _swiping?: boolean;
        swipeClass?: string;
    }

    interface ToastPayload {
        key?: string | number | null;
        message: string;
        details?: string[];
        type?: "success" | "error" | "warning" | "loading" | "info";
        duration?: number;
    }

    let toasts = $state<ToastItem[]>([]);
    let counter = 0;
    const swipeThreshold = 100;

    function toastMessage(message: string): string {
        if (!message) return "";
        // Callers often pass already-translated text. Only look up dotted i18n keys.
        if (!/^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$/i.test(message)) {
            return message;
        }
        try {
            return t(message);
        } catch {
            return message;
        }
    }

    function remove(id: number): void {
        const index = toasts.findIndex((entry) => entry.id === id);
        if (index !== -1) {
            const toast = toasts[index];
            if (toast.timer) {
                clearTimeout(toast.timer);
            }
            toasts.splice(index, 1);
            if (toast.key != null) {
                GlobalEmitter.emit("toast-dismissed", { key: toast.key });
            }
        }
    }

    function add(payload: ToastPayload): void {
        if (payload.key != null) {
            const existingIndex = toasts.findIndex((entry) => entry.key === payload.key);
            if (existingIndex !== -1) {
                const existing = toasts[existingIndex];
                if (existing.timer) {
                    clearTimeout(existing.timer);
                }
                existing.message = payload.message;
                existing.type = payload.type || "info";
                existing.duration = payload.duration !== undefined ? payload.duration : 5000;
                existing.details = Array.isArray(payload.details) ? payload.details : [];

                if (existing.duration > 0) {
                    existing.timer = setTimeout(() => {
                        remove(existing.id);
                    }, existing.duration);
                } else {
                    existing.timer = null;
                }
                return;
            }
        }

        const id = counter++;
        const duration = payload.duration !== undefined ? payload.duration : 5000;
        const newToast: ToastItem = {
            id,
            key: payload.key,
            message: payload.message,
            details: Array.isArray(payload.details) ? payload.details : [],
            type: payload.type || "info",
            duration,
            timer: null,
            _startX: 0,
            _swipeX: 0,
            _swiping: false,
            swipeClass: "",
        };

        if (duration > 0) {
            newToast.timer = setTimeout(() => {
                remove(id);
            }, duration);
        }

        toasts.push(newToast);
    }

    function toastClass(type: string): string {
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
    }

    function toastSwipeStyle(toast: ToastItem): string {
        const x = toast._swipeX || 0;
        if (x === 0) return "";
        const opacity = Math.max(0, 1 - Math.min(Math.abs(x) / swipeThreshold, 0.6));
        const transition = toast._swiping ? "none" : "transform 0.3s ease";
        return `transform: translateX(${x}px); transition: ${transition}; opacity: ${opacity};`;
    }

    function onTouchStart(event: TouchEvent, toast: ToastItem): void {
        if (event.touches.length !== 1) return;
        toast._startX = event.touches[0].clientX;
        toast._swipeX = 0;
        toast._swiping = true;
        toast.swipeClass = "";
    }

    function onTouchMove(event: TouchEvent, toast: ToastItem): void {
        if (!toast._swiping || event.touches.length !== 1 || toast._startX === undefined) return;
        toast._swipeX = event.touches[0].clientX - toast._startX;
    }

    function onTouchEnd(toast: ToastItem): void {
        if (!toast._swiping) return;
        toast._swiping = false;
        if (Math.abs(toast._swipeX || 0) >= swipeThreshold) {
            toast.swipeClass = (toast._swipeX || 0) > 0 ? "toast-swipe-out-right" : "toast-swipe-out-left";
            setTimeout(() => {
                remove(toast.id);
            }, 250);
        } else {
            toast._swipeX = 0;
        }
    }

    onMount(() => {
        const toastHandler = (payload: unknown) => {
            if (payload && typeof payload === "object") {
                add(payload as ToastPayload);
            }
        };
        const dismissHandler = (payload: unknown) => {
            const typed = payload as { key?: string | number | null } | undefined;
            if (typed && typed.key != null) {
                const index = toasts.findIndex((entry) => entry.key === typed.key);
                if (index !== -1) {
                    remove(toasts[index].id);
                }
            }
        };

        GlobalEmitter.on("toast", toastHandler);
        GlobalEmitter.on("toast-dismiss", dismissHandler);

        return () => {
            GlobalEmitter.off("toast", toastHandler);
            GlobalEmitter.off("toast-dismiss", dismissHandler);
            for (const toast of toasts) {
                if (toast.timer) {
                    clearTimeout(toast.timer);
                }
            }
        };
    });
</script>

<div
    class="fixed max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))] bottom-4 left-1/2 -translate-x-1/2 sm:left-auto sm:right-4 sm:translate-x-0 z-100 flex flex-col gap-2 pointer-events-none w-[calc(100%-2rem)] max-w-sm sm:w-auto sm:max-w-md"
>
    {#each toasts as toast (toast.id)}
        <div
            class="pointer-events-auto flex items-center p-4 w-full sm:min-w-[300px] sm:max-w-md rounded-xl shadow-lg border backdrop-blur-md transition-all duration-300 select-text touch-pan-y {toastClass(
                toast.type
            )} {toast.swipeClass || ''}"
            style={toastSwipeStyle(toast)}
            ontouchstart={(e) => onTouchStart(e, toast)}
            ontouchmove={(e) => onTouchMove(e, toast)}
            ontouchend={() => onTouchEnd(toast)}
            ontouchcancel={() => onTouchEnd(toast)}
            role="status"
        >
            <div class="mr-3 shrink-0">
                {#if toast.type === "success"}
                    <MaterialDesignIcon iconName="check-circle" class="h-6 w-6 text-green-500" />
                {:else if toast.type === "error"}
                    <MaterialDesignIcon iconName="alert-circle" class="h-6 w-6 text-red-500" />
                {:else if toast.type === "warning"}
                    <MaterialDesignIcon iconName="alert" class="h-6 w-6 text-amber-500" />
                {:else if toast.type === "loading"}
                    <MaterialDesignIcon iconName="loading" class="h-6 w-6 text-blue-500 animate-spin" />
                {:else}
                    <MaterialDesignIcon iconName="information" class="h-6 w-6 text-blue-500" />
                {/if}
            </div>

            <div class="flex-1 mr-2 text-sm font-medium text-sem-fg min-w-0">
                <div>{toastMessage(toast.message)}</div>
                {#if toast.details && toast.details.length > 0}
                    <ul class="mt-2 list-disc list-inside space-y-1 text-xs font-normal text-sem-fg-muted">
                        {#each toast.details as line, idx (idx)}
                            <li>{line}</li>
                        {/each}
                    </ul>
                {/if}
            </div>

            <button
                type="button"
                class="ml-auto inline-flex min-h-[44px] min-w-[44px] items-center justify-center -my-2 -mr-2 text-sem-fg-muted hover:text-sem-fg"
                aria-label={t("common.close")}
                onclick={() => remove(toast.id)}
            >
                <MaterialDesignIcon iconName="close" class="h-4 w-4" />
            </button>
        </div>
    {/each}
</div>

<style>
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
